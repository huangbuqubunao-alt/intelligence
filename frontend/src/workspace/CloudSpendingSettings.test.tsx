import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { CloudSpendingSettings } from "./CloudSpendingSettings";
import { UiLanguageProvider } from "./uiLanguage";

const hash = "a".repeat(64);
const initial = () => ({ revision: 0, policy: null, held_microunits: 0, held_requests: 0, remaining_microunits: 0,
  remaining_requests: 0, blocker: "CLOUD_SPENDING_POLICY_REQUIRED", price: { price_hash: hash,
    price_date: "2026-10-29", profile_id: "moonshot-k31-system-synthesis-v1-20261029", model: "kimi-k3.1-pro",
    input_microcny_per_token_worst: 26, output_microcny_per_token: 68, billing_guarantee: false } });
let state: unknown, conflict = false;
let mutations: Record<string, unknown>[], paths: string[];
beforeEach(() => {
  localStorage.setItem("yia.ui-language", "en"); state = initial(); mutations = []; paths = []; conflict = false;
  vi.stubGlobal("fetch", vi.fn(async (path: string, options?: RequestInit) => {
    paths.push(path);
    if (options?.method === "PUT") {
      const body = JSON.parse(String(options.body)); mutations.push(body);
      if (conflict) return { ok: false, status: 409, json: async () => ({ error: { code: "CLOUD_POLICY_CONFLICT", message: "conflict" } }) } as Response;
      state = { ...initial(), revision: 1, blocker: null, policy: { enabled: body.enabled, total_microunits: 8_000_000,
        per_request_microunits: 1_000_000, max_calls: body.max_calls, price_hash: hash } };
    }
    return { ok: true, json: async () => ({ spending_policy: state }) } as Response;
  }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); localStorage.clear(); });
const view = () => render(<UiLanguageProvider><CloudSpendingSettings /></UiLanguageProvider>);
async function fill() {
  fireEvent.change(await screen.findByLabelText("Cumulative reservation budget (CNY)"), { target: { value: "8.000000" } });
  fireEvent.change(screen.getByLabelText("Per-request reservation cap (CNY)"), { target: { value: "1.000000" } });
  fireEvent.change(screen.getByLabelText("Maximum cumulative requests"), { target: { value: "8" } });
  fireEvent.click(screen.getByLabelText("Enable this finite spending policy"));
  fireEvent.click(screen.getByLabelText("I accept this exact profile and price reference, and understand that each request needs separate confirmation."));
}

it("saves exact finite decimal strings only after explicit policy and price acknowledgement, without calling a model", async () => {
  view();
  expect((await screen.findByRole("button", { name: "Save finite spending limits" }) as HTMLButtonElement).disabled).toBe(true);
  await fill();
  fireEvent.click(screen.getByRole("button", { name: "Save finite spending limits" }));
  await screen.findByText("Spending limits saved. No request was authorized or sent, and model qualification is unchanged.");
  expect(screen.getByText("These limits apply to kimi-k3.1-pro. In Content, open cloud review and choose that model profile. Model qualification and separate request confirmation are still required.")).toBeTruthy();
  expect(mutations).toEqual([{ expected_revision: 0, enabled: true, total_cny: "8.000000", per_request_cny: "1.000000",
    max_calls: 8, accept_price_hash: hash, acknowledge: true }]);
  expect(paths.every(path => path.endsWith("/settings/cloud-spending-policy"))).toBe(true);
});

it("keeps the full draft on a conflict and requires reloading and explicit acknowledgement before resaving", async () => {
  conflict = true; view(); await fill();
  fireEvent.click(screen.getByRole("button", { name: "Save finite spending limits" }));
  await screen.findByText("Spending settings changed elsewhere. Your draft is kept; reload current totals, review and save explicitly.");
  expect((screen.getByLabelText("Cumulative reservation budget (CNY)") as HTMLInputElement).value).toBe("8.000000");
  expect((screen.getByLabelText("Enable this finite spending policy") as HTMLInputElement).checked).toBe(true);
  expect(mutations).toHaveLength(1);
  state = { ...initial(), revision: 3, held_microunits: 700_000, held_requests: 1 };
  fireEvent.click(screen.getByRole("button", { name: "Reload current spending totals (keep draft)" }));
  await screen.findByText(/CNY 0\.700000/);
  expect((screen.getByLabelText("Cumulative reservation budget (CNY)") as HTMLInputElement).value).toBe("8.000000");
  expect((screen.getByRole("button", { name: "Save finite spending limits" }) as HTMLButtonElement).disabled).toBe(true);
  conflict = false;
  fireEvent.click(screen.getByLabelText("I accept this exact profile and price reference, and understand that each request needs separate confirmation."));
  fireEvent.click(screen.getByRole("button", { name: "Save finite spending limits" }));
  await waitFor(() => expect(mutations).toHaveLength(2));
  expect(mutations[1].expected_revision).toBe(3);
});

it("shows unknown history as unknown and refuses to save instead of resetting totals", async () => {
  state = { ...initial(), revision: null, held_microunits: null, held_requests: null, blocker: "CLOUD_JOURNAL_HISTORY_MISSING" };
  view(); await screen.findByRole("alert");
  expect((screen.getByRole("button", { name: "Save finite spending limits" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByLabelText("Enable this finite spending policy") as HTMLInputElement).disabled).toBe(true);
  expect(mutations).toEqual([]);
});

it("rejects unverified price metadata and never offers a save", async () => {
  state = { ...initial(), price: { ...initial().price, price_hash: "unverified" } };
  view(); await screen.findByText("Spending history could not be verified. Cloud execution remains blocked.");
  expect(screen.queryByRole("button", { name: "Save finite spending limits" })).toBeNull();
  expect(mutations).toEqual([]);
});

it("provides Chinese cumulative limits and the no-execution explanation", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN"); view();
  expect(await screen.findByRole("heading", { name: "云端费用额度" })).toBeTruthy();
  expect(await screen.findByLabelText("累计预留预算（元）")).toBeTruthy();
  expect(screen.getByText(/不按月重置，不授予模型资格/)).toBeTruthy();
  expect(mutations).toEqual([]);
});
