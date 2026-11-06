import React from "react";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { ApiRequestError } from "../api/client";

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
let reviewCommands: unknown[];
let reviewResponse: (() => Promise<unknown>) | null, confirmResponse: (() => Promise<unknown>) | null;
const response = (body: unknown, ok = true) => Promise.resolve({ ok, json: async () => body } as Response);
beforeEach(() => {
  localStorage.setItem("yia.ui-language", "en");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/cloud-content";
  provider = "YOUTUBE"; returnedReview = review(); confirmations = []; requests = [];
  profiles = []; manual = false;
  reviewCommands = [];
  reviewResponse = null; confirmResponse = null;
  vi.stubGlobal("fetch", vi.fn(async (input: string, init?: RequestInit) => {
    requests.push(input);
    if (input.endsWith("/cloud-intelligence/profiles")) return response({ profiles });
    if (input.endsWith("/cloud-intelligence/review")) { reviewCommands.push(JSON.parse(String(init?.body)).command_id); return response({ review: await (reviewResponse?.() ?? returnedReview) }); }
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
  expect(within(screen.getByRole("region", { name: language === "en" ? "Cloud Intelligence disclosure" : "云端洞察数据与费用说明" })).getByRole("link", { name: language === "en" ? "Open model settings" : "打开模型设置" }).getAttribute("href")).toBe("#Settings/models/moonshot?return=%23Content%2Fcloud-content");
  expect((screen.getByRole("button", { name: language === "en" ? "Authorize this one cloud execution" : "授权本次云端执行" }) as HTMLButtonElement).disabled).toBe(true);
  expect(document.body.textContent).not.toMatch(/¥6\.50|Moonshot API usage/);
  expect(requests.filter(path => /credential|cloud-intelligence\/confirm/.test(path))).toEqual([]);
  expect(confirmations).toEqual([]);
  expect(screen.queryByText(/complete stored Summary as comparison context|待审核请求包含完整的已有摘要/)).toBeNull();
});

it.each(["CREDENTIAL_REQUIRED", "MODEL_UNQUALIFIED", "MODEL_UNAVAILABLE", "CLOUD_SPENDING_POLICY_REQUIRED", "CLOUD_EXECUTION_DISABLED", "INPUT_NOT_SUPPORTED", "EXECUTION_ALREADY_EXISTS", "UNRECOGNIZED_BLOCKER"])("keeps blocker %s closed", async blocker => {
  returnedReview = review({ readiness: { can_confirm: true, blockers: [blocker], budget_state: "BUDGET_UNVERIFIED" } });
  render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  const confirm = screen.getByRole("button", { name: "Authorize this one cloud execution" });
  expect((confirm as HTMLButtonElement).disabled).toBe(true);
  if (blocker === "CLOUD_EXECUTION_DISABLED") {
    expect(screen.getByText("Cloud execution is disabled in this environment. Reviewing or configuring a model does not enable paid requests.")).toBeTruthy();
    expect(screen.queryByText("This model has not qualified for this Intelligence task.")).toBeNull();
  }
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

it.each(["CANCELLED", "REJECTED_OUTPUT"].flatMap(status => ["en", "zh-CN"].map(language => ({ status, language }))))(
  "offers a new explicit manual cloud review after $status ($language), retaining original Content", async ({ status, language }) => {
    localStorage.setItem("yia.ui-language", language);
    const previousFetch = fetch;
    vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/videos/cloud-content")) return response({ ...detail(), manual_intelligence_eligible: true,
        waiting_model_executions: [], intelligence_result: { status, execution_id: "retained-old-execution", has_new_intelligence: false },
        local_intelligence: { request_state: "CONFIGURATION_REQUIRED", qualification_status: "NOT_QUALIFIED" } });
      return previousFetch(input, init);
    }));
    render(<App />);
    const button = await screen.findByRole("button", { name: language === "en" ? "Review cloud Intelligence" : "查看云端洞察预览" });
    expect(screen.getByText("Retained original transcript.")).toBeTruthy();
    expect(screen.getByText("Retained local Summary.")).toBeTruthy();
    expect(reviewCommands).toEqual([]); expect(confirmations).toEqual([]);
    fireEvent.click(button);
    expect(reviewCommands).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Prepare one request for review" : "准备审核本次请求" }));
    await screen.findByText(/offline-preview-provider/);
    expect(reviewCommands).toHaveLength(1); expect(reviewCommands[0]).toBeTruthy();
    expect(reviewCommands[0]).not.toBe("retained-old-execution");
    expect((screen.getByRole("button", { name: language === "en" ? "Authorize this one cloud execution" : "授权本次云端执行" }) as HTMLButtonElement).disabled).toBe(true);
    expect(confirmations).toEqual([]);
    expect(screen.getByText("Retained local Summary.")).toBeTruthy();
  },
);

it.each(["PENDING", "RUNNING", "AMBIGUOUS", "WAITING_BUDGET"])("does not add a cloud retry entry for protected %s", async status => {
  const previousFetch = fetch;
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => input.endsWith("/videos/cloud-content")
    ? response({ ...detail(), manual_intelligence_eligible: true, intelligence_result: { status, execution_id: "protected-old-execution" } })
    : previousFetch(input, init)));
  render(<App />); await screen.findByText("Retained local Summary.");
  expect(screen.queryByRole("button", { name: "Review cloud Intelligence" })).toBeNull();
  expect(requests.some(path => path.includes("cloud-intelligence"))).toBe(false);
  expect(reviewCommands).toEqual([]); expect(confirmations).toEqual([]);
});

it.each(["CANCELLED", "REJECTED_OUTPUT"])("requires backend manual eligibility before terminal %s cloud retry", async status => {
  const previousFetch = fetch;
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => input.endsWith("/videos/cloud-content")
    ? response({ ...detail(), manual_intelligence_eligible: false, intelligence_result: { status, execution_id: "ineligible-old-execution" } })
    : previousFetch(input, init)));
  render(<App />); await screen.findByText("Retained local Summary.");
  expect(screen.queryByRole("button", { name: "Review cloud Intelligence" })).toBeNull();
  expect(reviewCommands).toEqual([]); expect(confirmations).toEqual([]);
});

it("discards the old ticket after a new rejected execution and reviews with a fresh manual command", async () => {
  const v2 = "moonshot-k31-system-synthesis-v2-attribution-20261105";
  let execution = "retained-old-rejection";
  const previousFetch = fetch;
  profiles = [{ profile_id: "legacy", provider: "moonshot", model: "kimi-k2.6", qualified: false },
    { profile_id: v2, provider: "moonshot", model: "kimi-k3.1-pro", qualified: true }];
  returnedReview = review({ profile_id: v2, readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  confirmResponse = async () => { execution = "retained-new-rejection"; return { execution: { status: "REJECTED_OUTPUT" } }; };
  vi.stubGlobal("fetch", vi.fn((input: string, init?: RequestInit) => input.endsWith("/videos/cloud-content")
    ? response({ ...detail(), manual_intelligence_eligible: true,
      intelligence_result: { status: "REJECTED_OUTPUT", execution_id: execution, has_new_intelligence: false } })
    : previousFetch(input, init)));
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review cloud Intelligence" }));
  fireEvent.change(await screen.findByRole("combobox", { name: "Cloud model profile" }), { target: { value: v2 } });
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  await screen.findByText(/offline-preview-provider/);
  fireEvent.click(screen.getByRole("button", { name: "Authorize this one cloud execution" }));
  await waitFor(() => expect(confirmations).toHaveLength(1));
  await waitFor(() => expect(screen.queryByRole("region", { name: "Cloud Intelligence disclosure" })).toBeNull());
  expect(screen.getByText("Retained local Summary.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Review cloud Intelligence" }));
  expect((screen.getByRole("combobox", { name: "Cloud model profile" }) as HTMLSelectElement).value).toBe(v2);
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  await screen.findByText(/offline-preview-provider/);
  expect(reviewCommands).toHaveLength(2);
  expect(reviewCommands[0]).toBeTruthy(); expect(reviewCommands[1]).not.toBe(reviewCommands[0]);
  expect(confirmations).toHaveLength(1);
  expect(confirmations[0]).toEqual({ execution_id: "offline-execution", review_hash: ticket, authorize: true, profile_id: v2 });
});

it("reviews a finite backend synthesis profile with its own output bound and sends only its matching ticket", async () => {
  manual = true;
  profiles = [{ profile_id: "legacy", provider: "moonshot", model: "kimi-k2.6", adapter_available: true, qualified: true },
    { profile_id: "moonshot-k31-system-synthesis-v1-20261029", provider: "moonshot", model: "kimi-k3.1-pro", adapter_available: true, qualified: false }];
  returnedReview = review({ profile_id: "moonshot-k31-system-synthesis-v1-20261029",
    outgoing_request: { model: "offline-preview-model", max_completion_tokens: 5888, messages: [{ role: "user", content: 'UNTRUSTED_CURRENT_SUMMARY_BASELINE={"summary":"complete synthetic fixture"}' }] },
    readiness: { can_confirm: true, blockers: [], budget_state: "OFFLINE_TEST_ONLY" } });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review cloud Intelligence" }));
  fireEvent.change(await screen.findByRole("combobox", { name: "Cloud model profile" }), { target: { value: "moonshot-k31-system-synthesis-v1-20261029" } });
  expect(screen.queryByText(/complete stored Summary as comparison context/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  await screen.findByText(/offline-preview-provider/);
  expect(screen.getByText(/5888/, { selector: "p" })).toBeTruthy();
  expect(screen.getByText(/complete stored Summary as comparison context/)).toBeTruthy();
  expect(within(screen.getByRole("region", { name: "Cloud Intelligence disclosure" })).getByRole("link", { name: "Open model settings" }).getAttribute("href")).toBe("#Settings/models/moonshot?return=%23Content%2Fcloud-content");
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

it("shows the exact conservative reservation and actionable exhausted-budget link without dispatch", async () => {
  returnedReview = review({ spending: { reserve_microunits: 991_208, currency: "CNY" },
    readiness: { can_confirm: false, blockers: ["CLOUD_BUDGET_EXHAUSTED"], budget_state: "CLOUD_BUDGET_EXHAUSTED" } });
  render(<App />); await prepare();
  await screen.findByText(/CNY 0\.991208/);
  expect(screen.getByText("The cumulative reservation budget is exhausted. Held and unknown charges remain counted.")).toBeTruthy();
  expect(screen.getByRole("link", { name: "Configure spending limits" }).getAttribute("href")).toBe("#Settings/models/moonshot?return=%23Content%2Fcloud-content&panel=spending");
  expect((screen.getByRole("button", { name: "Authorize this one cloud execution" }) as HTMLButtonElement).disabled).toBe(true);
  expect(confirmations).toEqual([]);
});

it("guides a legacy review to the explicitly chosen synthesis profile for its separate finite policy", async () => {
  manual = true;
  profiles = [{ profile_id: "legacy", provider: "moonshot", model: "kimi-k2.6", adapter_available: true, qualified: true },
    { profile_id: "moonshot-k31-system-synthesis-v1-20261029", provider: "moonshot", model: "kimi-k3.1-pro", adapter_available: true, qualified: false }];
  returnedReview = review({ readiness: { can_confirm: false, blockers: ["CLOUD_SPENDING_POLICY_REQUIRED"], budget_state: "CLOUD_SPENDING_POLICY_REQUIRED" } });
  render(<App />); await prepare();
  expect(await screen.findByText("The finite spending settings cover kimi-k3.1-pro. For that policy, choose kimi-k3.1-pro in the cloud model profile list and prepare a new review.")).toBeTruthy();
  expect((screen.getByRole("combobox", { name: "Cloud model profile" }) as HTMLSelectElement).value).toBe("legacy");
  expect(confirmations).toEqual([]);
});

it("permits a fresh explicit review after proven zero-call abort, without resubmitting confirmation", async () => {
  manual = true;
  returnedReview = review({ readiness: { can_confirm: true, blockers: [], budget_state: "POLICY_READY" } });
  confirmResponse = async () => { throw new ApiRequestError({ code: "CLOUD_PRECLAIM_ABORTED", message: "synthetic preclaim abort" }); };
  render(<App />); await prepare(); await screen.findByText(/offline-preview-provider/);
  fireEvent.click(screen.getByRole("button", { name: "Authorize this one cloud execution" }));
  await screen.findByText("This request stopped safely before execution. No model was called; its original record is kept.");
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  await waitFor(() => expect(reviewCommands).toHaveLength(2));
  expect(reviewCommands[0]).toBeTruthy(); expect(reviewCommands[1]).not.toBe(reviewCommands[0]);
  expect(confirmations).toHaveLength(1);
});

it.each([true, false])("uses the explicitly selected attribution descriptor and rejects a mismatched review (%s)", async matching => {
  const v2 = "moonshot-k31-system-synthesis-v2-attribution-20261105";
  manual = true;
  profiles = [{ profile_id: "legacy", provider: "moonshot", model: "kimi-k2.6", qualified: false },
    { profile_id: "moonshot-k31-system-synthesis-v1-20261029", provider: "moonshot", model: "kimi-k3.1-pro", qualified: false },
    { profile_id: v2, provider: "moonshot", model: "kimi-k3.1-pro", qualified: false }];
  returnedReview = review({ profile_id: matching ? v2 : "moonshot-k31-system-synthesis-v1-20261029",
    outgoing_request: { model: "offline-preview-model", max_completion_tokens: 5888, messages: [{ role: "user", content: 'UNTRUSTED_CURRENT_SUMMARY_BASELINE={"summary":"retained"}' }] },
    readiness: { can_confirm: false, blockers: ["MODEL_UNQUALIFIED"], budget_state: "POLICY_READY" } });
  render(<App />);
  fireEvent.click(await screen.findByRole("button", { name: "Review cloud Intelligence" }));
  const select = await screen.findByRole("combobox", { name: "Cloud model profile" });
  expect(within(select).getByRole("option", { name: /Explicit speaker attribution policy/ })).toBeTruthy();
  fireEvent.change(select, { target: { value: v2 } });
  fireEvent.click(screen.getByRole("button", { name: "Prepare one request for review" }));
  if (matching) {
    await screen.findByText(/complete stored Summary as comparison context/);
    expect((screen.getByRole("button", { name: "Authorize this one cloud execution" }) as HTMLButtonElement).disabled).toBe(true);
  } else await screen.findByText("The cloud review could not be verified. Keep reading this Content, then prepare a new review or check model settings.");
  const post = vi.mocked(fetch).mock.calls.find(([path]) => String(path).endsWith("/cloud-intelligence/review"));
  expect(JSON.parse(String(post?.[1]?.body)).profile_id).toBe(v2);
  expect(confirmations).toHaveLength(0);
});


it.each([{ language: "en", matching: true, baseline: true }, { language: "zh-CN", matching: true, baseline: true },
  { language: "en", matching: false, baseline: true }, { language: "en", matching: true, baseline: false }])(
  "distinguishes the source-level profile and verifies its explicit review ($language, $matching, $baseline)", async ({ language, matching, baseline }) => {
    localStorage.setItem("yia.ui-language", language);
    const v3 = "moonshot-k31-system-synthesis-v3-source-level-20261106";
    manual = true;
    profiles = [{ profile_id: "moonshot-k31-system-synthesis-v1-20261029", provider: "moonshot", model: "kimi-k3.1-pro", qualified: false },
      { profile_id: "moonshot-k31-system-synthesis-v2-attribution-20261105", provider: "moonshot", model: "kimi-k3.1-pro", qualified: false },
      { profile_id: v3, provider: "moonshot", model: "kimi-k3.1-pro", qualified: false }];
    returnedReview = review({ profile_id: matching ? v3 : "moonshot-k31-system-synthesis-v2-attribution-20261105",
      outgoing_request: { model: "offline-preview-model", max_completion_tokens: 5888, messages: baseline
        ? [{ role: "user", content: 'UNTRUSTED_CURRENT_SUMMARY_BASELINE={"summary":"complete synthetic fixture"}' }] : [] },
      readiness: { can_confirm: false, blockers: ["MODEL_UNQUALIFIED"], budget_state: "POLICY_READY" } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: language === "en" ? "Review cloud Intelligence" : "查看云端洞察预览" }));
    const select = await screen.findByRole("combobox", { name: language === "en" ? "Cloud model profile" : "云端洞察模型方案" });
    expect(within(select).getByRole("option", { name: language === "en" ? /Source-level attribution/ : /按来源归因/ })).toBeTruthy();
    expect(new Set(Array.from((select as HTMLSelectElement).options).map(option => option.textContent)).size).toBe(3);
    expect(reviewCommands).toHaveLength(0); expect(confirmations).toHaveLength(0);
    fireEvent.change(select, { target: { value: v3 } });
    fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Prepare one request for review" : "准备审核本次请求" }));
    if (matching) {
      await screen.findByText(/offline-preview-provider/);
      expect((screen.getByRole("button", { name: language === "en" ? "Authorize this one cloud execution" : "授权本次云端执行" }) as HTMLButtonElement).disabled).toBe(true);
    } else await screen.findByText("The cloud review could not be verified. Keep reading this Content, then prepare a new review or check model settings.");
    const summaryDisclosure = screen.queryByText(/complete stored Summary as comparison context|待审核请求包含完整的已有摘要/);
    if (matching && baseline) expect(summaryDisclosure).toBeTruthy();
    else expect(summaryDisclosure).toBeNull();
    const post = vi.mocked(fetch).mock.calls.find(([path]) => String(path).endsWith("/cloud-intelligence/review"));
    expect(JSON.parse(String(post?.[1]?.body)).profile_id).toBe(v3);
    expect(confirmations).toHaveLength(0);
  },
);

it.each([{ language: "en", matching: true, baseline: true }, { language: "zh-CN", matching: true, baseline: true },
  { language: "en", matching: false, baseline: true }, { language: "en", matching: true, baseline: false }])(
  "distinguishes the readable-summary profile and verifies its explicit review ($language, $matching, $baseline)", async ({ language, matching, baseline }) => {
    localStorage.setItem("yia.ui-language", language);
    const v4 = "moonshot-k31-system-synthesis-v4-readable-summary-20261107";
    manual = true;
    profiles = [{ profile_id: "moonshot-k31-system-synthesis-v1-20261029", provider: "moonshot", model: "kimi-k3.1-pro", qualified: false },
      { profile_id: "moonshot-k31-system-synthesis-v2-attribution-20261105", provider: "moonshot", model: "kimi-k3.1-pro", qualified: false },
      { profile_id: "moonshot-k31-system-synthesis-v3-source-level-20261106", provider: "moonshot", model: "kimi-k3.1-pro", qualified: false },
      { profile_id: v4, provider: "moonshot", model: "kimi-k3.1-pro", qualified: false }];
    returnedReview = review({ profile_id: matching ? v4 : "moonshot-k31-system-synthesis-v2-attribution-20261105",
      outgoing_request: { model: "offline-preview-model", max_completion_tokens: 5888, messages: baseline
        ? [{ role: "user", content: 'UNTRUSTED_CURRENT_SUMMARY_BASELINE={"summary":"complete synthetic fixture"}' }] : [] },
      readiness: { can_confirm: false, blockers: ["MODEL_UNQUALIFIED"], budget_state: "POLICY_READY" } });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: language === "en" ? "Review cloud Intelligence" : "查看云端洞察预览" }));
    const select = await screen.findByRole("combobox", { name: language === "en" ? "Cloud model profile" : "云端洞察模型方案" });
    expect(within(select).getByRole("option", { name: language === "en" ? /Complete Summary comparison/ : /完整摘要对照/ })).toBeTruthy();
    expect(new Set(Array.from((select as HTMLSelectElement).options).map(option => option.textContent)).size).toBe(4);
    expect(reviewCommands).toHaveLength(0); expect(confirmations).toHaveLength(0);
    fireEvent.change(select, { target: { value: v4 } });
    fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Prepare one request for review" : "准备审核本次请求" }));
    if (matching) {
      await screen.findByText(/offline-preview-provider/);
      expect((screen.getByRole("button", { name: language === "en" ? "Authorize this one cloud execution" : "授权本次云端执行" }) as HTMLButtonElement).disabled).toBe(true);
    } else await screen.findByText("The cloud review could not be verified. Keep reading this Content, then prepare a new review or check model settings.");
    const summaryDisclosure = screen.queryByText(/complete stored Summary as comparison context|待审核请求包含完整的已有摘要/);
    if (matching && baseline) expect(summaryDisclosure).toBeTruthy();
    else expect(summaryDisclosure).toBeNull();
    const post = vi.mocked(fetch).mock.calls.find(([path]) => String(path).endsWith("/cloud-intelligence/review"));
    expect(JSON.parse(String(post?.[1]?.body)).profile_id).toBe(v4);
    expect(confirmations).toHaveLength(0);
  },
);
