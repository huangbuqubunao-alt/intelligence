import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

it.each(["10000", "abc", "0", "-1", "1.5", "1001"])("explains invalid count %s, keeps the draft and prevents a silent save", async invalid => {
  const user = userEvent.setup(); view(); await fill();
  const input = screen.getByLabelText("Maximum cumulative requests") as HTMLInputElement;
  await user.clear(input); await user.type(input, invalid);
  expect(screen.getByRole("alert").textContent).toBe("Enter a whole request count from 1 to 1000.");
  expect(input.getAttribute("aria-invalid")).toBe("true");
  const save = screen.getByRole("button", { name: "Save finite spending limits" }) as HTMLButtonElement;
  expect(save.disabled).toBe(true); await user.click(save);
  expect(input.value).toBe(invalid);
  expect((screen.getByLabelText("Cumulative reservation budget (CNY)") as HTMLInputElement).value).toBe("8.000000");
  expect(mutations).toEqual([]);
  expect(paths.every(path => path.endsWith("/settings/cloud-spending-policy"))).toBe(true);
});

it.each(["1", "1000"])("accepts the inclusive count boundary %s through the settings endpoint only", async count => {
  const user = userEvent.setup(); view(); await fill();
  const input = screen.getByLabelText("Maximum cumulative requests") as HTMLInputElement;
  await user.clear(input); await user.type(input, count);
  expect(screen.queryByRole("alert")).toBeNull();
  await user.click(screen.getByRole("button", { name: "Save finite spending limits" }));
  await waitFor(() => expect(mutations).toHaveLength(1));
  expect(mutations[0].max_calls).toBe(Number(count));
  expect(paths.every(path => path.endsWith("/settings/cloud-spending-policy"))).toBe(true);
});

it("requires a fresh acknowledgement for the declared attribution policy while retaining all limits and holds", async () => {
  const original = initial(), v2 = { ...original.price, profile_id: "moonshot-k31-system-synthesis-v2-attribution-20261105", price_hash: "b".repeat(64) };
  state = { ...original, held_microunits: 700_000, held_requests: 1, prices: [original.price, v2] };
  vi.stubGlobal("fetch", vi.fn(async (path: string, options?: RequestInit) => {
    paths.push(path);
    if (options?.method === "PUT") {
      const body = JSON.parse(String(options.body)); mutations.push(body);
      state = { ...original, price: v2, prices: [original.price, v2], revision: 1, held_microunits: 700_000, held_requests: 1,
        policy: { enabled: true, total_microunits: 8_000_000, per_request_microunits: 1_000_000, max_calls: 8, price_hash: v2.price_hash } };
    }
    return { ok: true, json: async () => ({ spending_policy: state }) } as Response;
  }));
  view(); await fill();
  fireEvent.change(screen.getByRole("combobox", { name: "Model policy and price reference" }), { target: { value: v2.profile_id } });
  const ack = screen.getByLabelText("I accept this exact profile and price reference, and understand that each request needs separate confirmation.") as HTMLInputElement;
  expect(ack.checked).toBe(false);
  expect((screen.getByRole("button", { name: "Save finite spending limits" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByLabelText("Cumulative reservation budget (CNY)") as HTMLInputElement).value).toBe("8.000000");
  expect((screen.getByLabelText("Maximum cumulative requests") as HTMLInputElement).value).toBe("8");
  expect(mutations).toHaveLength(0);
  fireEvent.click(ack); fireEvent.click(screen.getByRole("button", { name: "Save finite spending limits" }));
  await waitFor(() => expect(mutations).toHaveLength(1));
  expect(mutations[0].accept_price_hash).toBe(v2.price_hash);
  expect((screen.getByRole("combobox", { name: "Model policy and price reference" }) as HTMLSelectElement).value).toBe(v2.profile_id);
  expect(screen.getByText(/CNY 0\.700000/)).toBeTruthy();
  expect(paths.every(path => path.endsWith("/settings/cloud-spending-policy"))).toBe(true);
});

it("accepts the three declared policies and saves the source-level price only after fresh acknowledgement", async () => {
  const original = initial();
  const v2 = { ...original.price, profile_id: "moonshot-k31-system-synthesis-v2-attribution-20261105", price_hash: "b".repeat(64) };
  const v3 = { ...original.price, profile_id: "moonshot-k31-system-synthesis-v3-source-level-20261106", price_hash: "c".repeat(64) };
  const prices = [original.price, v2, v3];
  state = { ...original, held_microunits: 700_000, held_requests: 1, prices };
  vi.stubGlobal("fetch", vi.fn(async (path: string, options?: RequestInit) => {
    paths.push(path);
    if (options?.method === "PUT") {
      const body = JSON.parse(String(options.body)); mutations.push(body);
      state = { ...original, price: v3, prices, revision: 1, held_microunits: 700_000, held_requests: 1,
        policy: { enabled: true, total_microunits: 8_000_000, per_request_microunits: 1_000_000, max_calls: 8, price_hash: v3.price_hash } };
    }
    return { ok: true, json: async () => ({ spending_policy: state }) } as Response;
  }));
  view(); await fill();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Original synthesis policy" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Explicit speaker attribution policy" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Source-level attribution" })).toBeTruthy();
  const select = screen.getByRole("combobox", { name: "Model policy and price reference" });
  fireEvent.change(select, { target: { value: v3.profile_id } });
  const acknowledgement = screen.getByLabelText("I accept this exact profile and price reference, and understand that each request needs separate confirmation.") as HTMLInputElement;
  expect(acknowledgement.checked).toBe(false);
  expect((screen.getByRole("button", { name: "Save finite spending limits" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByLabelText("Cumulative reservation budget (CNY)") as HTMLInputElement).value).toBe("8.000000");
  expect(screen.getByText(/CNY 0\.700000/)).toBeTruthy();
  expect(mutations).toEqual([]);
  fireEvent.click(acknowledgement);
  fireEvent.click(screen.getByRole("button", { name: "Save finite spending limits" }));
  await screen.findByText("Spending limits saved. No request was authorized or sent, and model qualification is unchanged.");
  expect(mutations).toEqual([{ expected_revision: 0, enabled: true, total_cny: "8.000000", per_request_cny: "1.000000",
    max_calls: 8, accept_price_hash: v3.price_hash, acknowledge: true }]);
  expect((select as HTMLSelectElement).value).toBe(v3.profile_id);
  expect(screen.getByText(/CNY 0\.700000/)).toBeTruthy();
  expect(paths.every(path => path.endsWith("/settings/cloud-spending-policy"))).toBe(true);
});

it("accepts the four declared policies and saves the readable-summary price only after fresh acknowledgement", async () => {
  const original = initial();
  const v2 = { ...original.price, profile_id: "moonshot-k31-system-synthesis-v2-attribution-20261105", price_hash: "b".repeat(64) };
  const v3 = { ...original.price, profile_id: "moonshot-k31-system-synthesis-v3-source-level-20261106", price_hash: "c".repeat(64) };
  const v4 = { ...original.price, profile_id: "moonshot-k31-system-synthesis-v4-readable-summary-20261107", price_hash: "d".repeat(64) };
  const prices = [original.price, v2, v3, v4];
  state = { ...original, held_microunits: 700_000, held_requests: 1, prices };
  vi.stubGlobal("fetch", vi.fn(async (path: string, options?: RequestInit) => {
    paths.push(path);
    if (options?.method === "PUT") {
      const body = JSON.parse(String(options.body)); mutations.push(body);
      state = { ...original, price: v4, prices, revision: 1, held_microunits: 700_000, held_requests: 1,
        policy: { enabled: true, total_microunits: 8_000_000, per_request_microunits: 1_000_000, max_calls: 8, price_hash: v4.price_hash } };
    }
    return { ok: true, json: async () => ({ spending_policy: state }) } as Response;
  }));
  view(); await fill();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Original synthesis policy" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Explicit speaker attribution policy" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Source-level attribution" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Complete Summary comparison" })).toBeTruthy();
  const select = screen.getByRole("combobox", { name: "Model policy and price reference" });
  fireEvent.change(select, { target: { value: v4.profile_id } });
  const acknowledgement = screen.getByLabelText("I accept this exact profile and price reference, and understand that each request needs separate confirmation.") as HTMLInputElement;
  expect(acknowledgement.checked).toBe(false);
  expect((screen.getByRole("button", { name: "Save finite spending limits" }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByLabelText("Cumulative reservation budget (CNY)") as HTMLInputElement).value).toBe("8.000000");
  expect(screen.getByText(/CNY 0\.700000/)).toBeTruthy();
  expect(mutations).toEqual([]);
  fireEvent.click(acknowledgement);
  fireEvent.click(screen.getByRole("button", { name: "Save finite spending limits" }));
  await screen.findByText("Spending limits saved. No request was authorized or sent, and model qualification is unchanged.");
  expect(mutations).toEqual([{ expected_revision: 0, enabled: true, total_cny: "8.000000", per_request_cny: "1.000000",
    max_calls: 8, accept_price_hash: v4.price_hash, acknowledge: true }]);
  expect((select as HTMLSelectElement).value).toBe(v4.profile_id);
  expect(screen.getByText(/CNY 0\.700000/)).toBeTruthy();
  expect(paths.every(path => path.endsWith("/settings/cloud-spending-policy"))).toBe(true);
});

it("names the source-level policy in Chinese", async () => {
  const original = initial();
  state = { ...original, prices: [original.price,
    { ...original.price, profile_id: "moonshot-k31-system-synthesis-v3-source-level-20261106", price_hash: "c".repeat(64) }] };
  localStorage.setItem("yia.ui-language", "zh-CN"); view();
  expect(await screen.findByRole("option", { name: "kimi-k3.1-pro · 按来源归因" })).toBeTruthy();
  expect(mutations).toEqual([]);
});

it.each(["unknown", "duplicate", "fifth"])("refuses a %s profile catalog without offering a spending save", async invalid => {
  const original = initial();
  const prices = [original.price,
    { ...original.price, profile_id: "moonshot-k31-system-synthesis-v2-attribution-20261105", price_hash: "b".repeat(64) },
    { ...original.price, profile_id: "moonshot-k31-system-synthesis-v3-source-level-20261106", price_hash: "c".repeat(64) }];
  if (invalid === "unknown") prices[2] = { ...prices[2], profile_id: "unknown-policy" };
  if (invalid === "duplicate") prices[2] = prices[1];
  if (invalid === "fifth") prices.push(
    { ...original.price, profile_id: "moonshot-k31-system-synthesis-v4-readable-summary-20261107" },
    { ...original.price, profile_id: "unknown-policy" });
  state = { ...original, prices }; view();
  await screen.findByText("Spending history could not be verified. Cloud execution remains blocked.");
  expect(screen.queryByRole("button", { name: "Save finite spending limits" })).toBeNull();
  expect(mutations).toEqual([]);
});

it("names the readable-summary policy in Chinese", async () => {
  const original = initial();
  state = { ...original, prices: [original.price,
    { ...original.price, profile_id: "moonshot-k31-system-synthesis-v4-readable-summary-20261107", price_hash: "d".repeat(64) }] };
  localStorage.setItem("yia.ui-language", "zh-CN"); view();
  expect(await screen.findByRole("option", { name: "kimi-k3.1-pro · 完整摘要对照" })).toBeTruthy();
  expect(mutations).toEqual([]);
});

it("accepts the v5 judgment policy as a fifth declared price reference and labels it", async () => {
  const original = initial();
  const ids = ["moonshot-k31-system-synthesis-v2-attribution-20261105", "moonshot-k31-system-synthesis-v3-source-level-20261106",
    "moonshot-k31-system-synthesis-v4-readable-summary-20261107", "moonshot-k31-system-synthesis-v5-judgment-stream-20261112"];
  const prices = [original.price, ...ids.map((profile_id, index) => ({ ...original.price, profile_id, price_hash: "bcde"[index].repeat(64) }))];
  state = { ...original, prices };
  vi.stubGlobal("fetch", vi.fn(async (path: string) => {
    paths.push(path);
    return { ok: true, json: async () => ({ spending_policy: state }) } as Response;
  }));
  view(); await fill();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Judgment beyond the complete Summary" })).toBeTruthy();
  expect(screen.getByRole("option", { name: "kimi-k3.1-pro · Complete Summary comparison" })).toBeTruthy();
  expect(mutations).toEqual([]);
});

it("still rejects an undeclared sixth price reference", async () => {
  const original = initial();
  const prices = [original.price, ...["a", "b", "c", "d", "e"].map(letter => ({ ...original.price, price_hash: letter.repeat(64) }))];
  state = { ...original, prices };
  vi.stubGlobal("fetch", vi.fn(async (path: string) => {
    paths.push(path);
    return { ok: true, json: async () => ({ spending_policy: state }) } as Response;
  }));
  view();
  await waitFor(() => expect(paths.length).toBeGreaterThan(0));
  expect(screen.queryByRole("option", { name: /Judgment beyond the complete Summary/ })).toBeNull();
});
