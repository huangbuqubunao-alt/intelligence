import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { KnowledgeDelta, KnowledgeDeltaProjection } from "./KnowledgeDelta";
import { UiLanguageProvider } from "./uiLanguage";

const kinds = ["content_completed", "intelligence_added", "intelligence_revised", "topic_updated", "source_health"] as const;
const fixture = (): KnowledgeDeltaProjection => ({
  window_start: "2026-09-26T08:00:00.000000Z", window_end: "2026-10-03T08:00:00.000000Z",
  timezone: "Asia/Shanghai", status: "available", detail_limit: 2,
  categories: kinds.map(kind => ({ kind, status: "available", count: 0, items: [] })),
});
const load = (delta: KnowledgeDeltaProjection, onOpen = vi.fn()) => {
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ knowledge_delta: delta }) })));
  render(<UiLanguageProvider><KnowledgeDelta refresh={0} onOpen={onOpen} /></UiLanguageProvider>);
  return onOpen;
};
beforeEach(() => { localStorage.setItem("yia.ui-language", "en"); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("shows a truthful empty seven-day surface", async () => {
  load(fixture());
  expect(await screen.findByText("No meaningful knowledge changes in the last 7 days.")).toBeTruthy();
  expect(screen.getByRole("heading", { name: "What changed in the last 7 days?" })).toBeTruthy();
  expect(screen.queryByText(/since you last/i)).toBeNull();
});

it("shows factual counts, revisions, evidence replacement and links", async () => {
  const delta = fixture();
  delta.categories[2] = { kind: "intelligence_revised", status: "available", count: 34, items: [{
    id: "change", kind: "intelligence_revised", label: "Intelligence revised", title: "Original Content title",
    target: { kind: "intelligence", id: "intel" }, occurred_at: delta.window_end,
    facts: { revision_count: 4, evidence_before: 2, evidence_after: 2, evidence_set_changed: true,
      state_before: "Confirmed", state_after: "Disputed", state_changed_at: delta.window_end },
  }] };
  const open = load(delta);
  const region = await screen.findByRole("region", { name: "What changed in the last 7 days?" });
  expect(within(region).getByText("34")).toBeTruthy();
  expect(within(region).getByText(/Evidence set changed: 2 → 2/)).toBeTruthy();
  expect(within(region).getByText(/Recorded state: Confirmed → Disputed/)).toBeTruthy();
  expect(within(region).getByText(/Showing 1 of 34/)).toBeTruthy();
  fireEvent.click(within(region).getByRole("button", { name: /Open Intelligence/ }));
  expect(open).toHaveBeenCalledWith({ kind: "intelligence", id: "intel" });
});

it("labels partial counts unavailable and never calls partial data empty", async () => {
  const delta = fixture();
  delta.status = "partial";
  delta.categories[3] = { kind: "topic_updated", status: "unavailable", count: null, items: [] };
  load(delta);
  expect(await screen.findByText("Some changes could not be checked. Counts below cover available sources only.")).toBeTruthy();
  expect(screen.queryByText("No meaningful knowledge changes in the last 7 days.")).toBeNull();
  expect(screen.getByText("Unavailable")).toBeTruthy();
});

it("localizes Chinese product copy and recorded states without enums", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const delta = fixture();
  delta.categories[2] = { kind: "intelligence_revised", status: "available", count: 1, items: [{
    id: "change", kind: "intelligence_revised", label: "Intelligence revised", title: "原始内容",
    target: { kind: "intelligence", id: "intel" }, occurred_at: delta.window_end,
    facts: { revision_count: 1, state_before: "Pending confirmation", state_after: "Confirmed" },
  }] };
  load(delta);
  const region = await screen.findByRole("region", { name: "最近 7 天发生了什么变化？" });
  await within(region).findByText("原始内容");
  expect(region.textContent).toContain("记录的验证状态：待确认 → 已确认");
  expect(region.textContent).not.toMatch(/intelligence_revised|CONFIRMED|Pending confirmation|Recorded state|Evidence|Showing/);
});

it("keeps unavailable data distinct from zero", async () => {
  const delta = fixture();
  delta.status = "unavailable";
  delta.categories = delta.categories.map(category => ({ ...category, status: "unavailable", count: null }));
  load(delta);
  expect(await screen.findByText("Recent changes are unavailable. Try again shortly.")).toBeTruthy();
  expect(screen.queryByText("No meaningful knowledge changes in the last 7 days.")).toBeNull();
});


it("localizes transport failure and retries without exposing diagnostics", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const request = vi.fn().mockRejectedValueOnce(new Error("PRIVATE English stack and path"))
    .mockResolvedValueOnce({ ok: true, json: async () => ({ knowledge_delta: fixture() }) });
  vi.stubGlobal("fetch", request);
  render(<UiLanguageProvider><KnowledgeDelta refresh={0} onOpen={vi.fn()} /></UiLanguageProvider>);
  expect(await screen.findByText("暂时无法查看最近的变化，请稍后重试。")).toBeTruthy();
  expect(document.body.textContent).not.toContain("PRIVATE");
  fireEvent.click(screen.getByRole("button", { name: "重试" }));
  expect(await screen.findByText("最近 7 天没有明显的知识变化。")).toBeTruthy();
  expect(request).toHaveBeenCalledTimes(2);
});

it("shows loading until an authoritative result arrives", async () => {
  vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
  render(<UiLanguageProvider><KnowledgeDelta refresh={0} onOpen={vi.fn()} /></UiLanguageProvider>);
  expect(screen.getByRole("status").textContent).toBe("Checking recent changes…");
  expect(screen.queryByText("No meaningful knowledge changes in the last 7 days.")).toBeNull();
});
