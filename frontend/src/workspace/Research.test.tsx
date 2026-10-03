import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Research } from "./Research";
import { UiLanguageProvider } from "./uiLanguage";

const packet = {
  research_id: "a".repeat(64), question: "What evidence?", output_language: "en", assembled_at: "2026-10-03T08:00:00Z",
  scope: [{ content_id: "one", title: "Original Content" }], material_status: "EVIDENCE_AVAILABLE",
  evidence: [{ evidence_id: "durable", content_id: "one", artifact_id: "artifact", excerpt: "Original authority.", start_ms: 1000, end_ms: 2000, source_language: "en", lineage_kind: "ORIGINAL_TRANSCRIPT", role: "PRIMARY_ORIGINAL", created_at: "2026-10-02T08:00:00Z" }],
  intelligence: [], evidence_candidates: 1, intelligence_candidates: 0, retrieval_truncated: false,
};
const envelope = () => ({ research: { result_identity: "r", provenance_status: "VERIFIED", packet } });
const setup = (override?: (path: string, method?: string) => object | undefined) => {
  const request = vi.fn(async (path: string, options?: RequestInit) => {
    const custom = override?.(path, options?.method);
    const data = custom || (path.startsWith("/api/v1/research/scope") ? { content: [{ content_id: "one", title: "Original Content", channel_name: "Source" }], total: 1, offset: 0, limit: 50 }
      : path === "/api/v1/research" && !options?.method ? { research: [], total: 0, offset: 0, limit: 25 }
      : /\/history(?:\?|$)/.test(path) ? { revisions: [], current_revision_id: "r", current_available: true, unavailable_count: 0, has_more: false, next_cursor: null, limit: 25 } : envelope());
    return { ok: !("error" in data), json: async () => data };
  });
  vi.stubGlobal("fetch", request);
  const onOpen = vi.fn();
  render(<UiLanguageProvider><Research onOpen={onOpen} /></UiLanguageProvider>);
  return { request, onOpen };
};
beforeEach(() => { location.hash = "Research"; localStorage.setItem("yia.ui-language", "en"); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it("shows the empty state and local-only contract", async () => {
  setup();
  expect(await screen.findByText("No Research yet. Start with a question and selected library Content.")).toBeTruthy();
  expect(screen.getByText("Research uses only your existing library. No web exploration or model call.")).toBeTruthy();
});

it("rejects invalid question and empty scope before dispatch", async () => {
  const { request } = setup();
  fireEvent.click(await screen.findByRole("button", { name: "New Research" }));
  await screen.findByRole("checkbox", { name: /Original Content/ });
  fireEvent.click(screen.getByRole("button", { name: "Assemble library packet" }));
  expect(screen.getByRole("alert").textContent).toContain("Enter a question");
  fireEvent.change(screen.getByLabelText("Research question"), { target: { value: "What evidence?" } });
  fireEvent.click(screen.getByRole("button", { name: "Assemble library packet" }));
  expect(screen.getByRole("alert").textContent).toBe("Select at least one Content item.");
  expect(request.mock.calls.every(call => call[1]?.method !== "POST")).toBe(true);
});

it("creates a packet with explicit scope and traces original Evidence", async () => {
  const { request, onOpen } = setup();
  fireEvent.click(await screen.findByRole("button", { name: "New Research" }));
  fireEvent.change(screen.getByLabelText("Research question"), { target: { value: "What evidence?" } });
  fireEvent.click(await screen.findByRole("checkbox", { name: /Original Content/ }));
  fireEvent.click(screen.getByRole("button", { name: "Assemble library packet" }));
  expect(await screen.findByText("Original authority.")).toBeTruthy();
  expect(screen.getByText(/No Research synthesis model ran/)).toBeTruthy();
  const post = request.mock.calls.find(call => call[1]?.method === "POST");
  expect(JSON.parse(post?.[1]?.body as string)).toEqual({ question: "What evidence?", content_ids: ["one"] });
  fireEvent.click(screen.getByRole("button", { name: "Open Content and Evidence" }));
  expect(onOpen).toHaveBeenCalledWith("content", "one", "durable");
});

it("reopens the persisted current result through its route", async () => {
  location.hash = `Research/${packet.research_id}`;
  setup();
  expect(await screen.findByText("Original authority.")).toBeTruthy();
  expect(await screen.findByRole("heading", { name: "Research History" })).toBeTruthy();
  expect(screen.queryByText(/Compare versions|Diff/)).toBeNull();
});

it("localizes corrupted results without raw backend diagnostics", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = `Research/${packet.research_id}`;
  setup(path => path.endsWith(packet.research_id) ? { error: { code: "RESEARCH_CORRUPTED_RESULT", message: "PRIVATE backend diagnostic" } } : undefined);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(document.body.textContent).toContain("完整性检查");
  expect(document.body.textContent).not.toMatch(/PRIVATE|RESEARCH_CORRUPTED/);
});

it("shows insufficient material honestly in Chinese", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = `Research/${packet.research_id}`;
  setup(path => path.endsWith(packet.research_id) ? { research: { ...envelope().research, packet: { ...packet, material_status: "INSUFFICIENT_MATERIAL", evidence: [] } } } : undefined);
  expect(await screen.findByText(/未找到匹配的权威证据/)).toBeTruthy();
  expect(document.body.textContent).not.toMatch(/INSUFFICIENT_MATERIAL|No matching|Unresolved points/);
});

it("renders untrusted questions as text", async () => {
  location.hash = `Research/${packet.research_id}`;
  setup(path => path.endsWith(packet.research_id) ? { research: { ...envelope().research, packet: { ...packet, question: "<script>bad()</script>" } } } : undefined);
  expect(await screen.findByText("<script>bad()</script>")).toBeTruthy();
  expect(document.querySelector(".research-result script")).toBeNull();
});

it("localizes interpretation classes, states and every Evidence stance", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = `Research/${packet.research_id}`;
  setup(path => path.endsWith(packet.research_id) ? { research: { ...envelope().research, packet: { ...packet, intelligence: ["supporting", "contradicting", "conditional", null].map((stance, index) => ({ intelligence_id: `i${index}`, revision_id: `r${index}`, content_id: "one", conclusion: "Source interpretation", claim_kind: "SYSTEM_INFERENCE", state: "UPDATED", evidence_ids: ["durable"], stances: [stance] })) } } } : undefined);
  await screen.findAllByText("Source interpretation");
  expect(document.body.textContent).not.toMatch(/Supporting|Contradicting|Conditional|Relation not determined|Recorded state|INFERENCE|UPDATED/);
  expect(document.body.textContent).toContain("支持");
  expect(document.body.textContent).toContain("反驳");
  expect(document.body.textContent).toContain("附带条件");
});


it("retains every admitted claim classification without inflating legacy facts", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = `Research/${packet.research_id}`;
  setup(path => path.endsWith(packet.research_id) ? { research: { ...envelope().research, packet: { ...packet, intelligence: ["FACT", "RUMOR", "SYSTEM_INFERENCE"].map((claim, index) => ({ intelligence_id: `i${index}`, revision_id: `r${index}`, content_id: "one", conclusion: "Recorded source claim", claim_kind: claim, state: "NEW", evidence_ids: ["durable"], stances: [null] })) } } } : undefined);
  await screen.findAllByText("Recorded source claim");
  expect(document.body.textContent).toContain("已记录的事实分类");
  expect(document.body.textContent).toContain("未经确认的传闻");
  expect(document.body.textContent).toContain("系统推断");
  expect(document.body.textContent).not.toMatch(/Recorded interpretation|FACT|RUMOR|SYSTEM_INFERENCE/);
});

it.each(["en", "zh-CN"])("opens an exact read-only old packet and returns to current in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  location.hash = `Research/${packet.research_id}`;
  const oldId = "b".repeat(64);
  const text = (en: string, zh: string) => language === "en" ? en : zh;
  const { request, onOpen } = setup(path => path.endsWith("/history") ? {
    revisions: [{ revision_id: oldId, assembled_at: packet.assembled_at, question: packet.question, output_language: "en", scope_count: 1, evidence_count: 1, intelligence_count: 0, status: "EVIDENCE_AVAILABLE" }],
    current_revision_id: "r", current_available: true, unavailable_count: 0, has_more: false, next_cursor: null, limit: 25,
  } : path.endsWith(oldId) ? { research: { ...envelope().research, result_identity: oldId, packet: { ...packet, evidence: [{ ...packet.evidence[0], evidence_id: "old-evidence", excerpt: "Exact old source." }] } } } : undefined);
  fireEvent.click(await screen.findByRole("button", { name: new RegExp(text("Open previous version", "打开历史版本")) }));
  expect(await screen.findByText("Exact old source.")).toBeTruthy();
  expect(screen.getByRole("heading", { name: text("Previous Research version", "研究历史版本") })).toBeTruthy();
  expect(screen.queryByText("Original authority.")).toBeNull();
  expect(location.hash).toBe(`#Research/${packet.research_id}/history/${oldId}`);
  fireEvent.click(screen.getByRole("button", { name: text("Open Content and Evidence", "打开内容与证据") }));
  expect(onOpen).toHaveBeenCalledWith("content", "one", "old-evidence");
  expect(request.mock.calls.some(([path]) => path.endsWith(`/history/${oldId}`))).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: text("Open current version", "打开当前版本") }));
  expect(await screen.findByText("Original authority.")).toBeTruthy();
  expect(screen.getByRole("heading", { name: text("Current Research version", "研究当前版本") })).toBeTruthy();
  if (language === "zh-CN") expect(document.body.textContent).not.toMatch(/Read-only|Research History|EVIDENCE_AVAILABLE|VERIFIED/);
});

it("reopens a historical deep route explicitly", async () => {
  const oldId = "b".repeat(64);
  location.hash = `Research/${packet.research_id}/history/${oldId}`;
  const { request } = setup();
  expect(await screen.findByRole("heading", { name: "Previous Research version" })).toBeTruthy();
  expect(request.mock.calls.some(([path]) => path.endsWith(`/history/${oldId}`))).toBe(true);
});

it("paginates without accumulating an unbounded rendered list", async () => {
  location.hash = `Research/${packet.research_id}`;
  const cursor = `${packet.research_id}:30:5`;
  setup(path => path.includes("/history") ? {
    revisions: Array.from({ length: path.includes("?") ? 4 : 25 }, (_, i) => ({ revision_id: String(i), assembled_at: packet.assembled_at, question: packet.question, output_language: "en", scope_count: 1, evidence_count: 1, intelligence_count: 0, status: "EVIDENCE_AVAILABLE" })),
    current_revision_id: "r", current_available: true, unavailable_count: 0, has_more: !path.includes("?"), next_cursor: cursor, limit: 25,
  } : undefined);
  expect((await screen.findAllByRole("button", { name: /Open previous version/ })).length).toBe(25);
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  expect((await screen.findAllByRole("button", { name: /Open previous version/ })).length).toBe(4);
  fireEvent.click(screen.getByRole("button", { name: "Previous" }));
  expect((await screen.findAllByRole("button", { name: /Open previous version/ })).length).toBe(25);
});

it("discloses excluded corrupt versions without showing their payload or claiming an empty complete history", async () => {
  location.hash = `Research/${packet.research_id}`;
  setup(path => path.endsWith("/history") ? { revisions: [], current_revision_id: "r", current_available: true, unavailable_count: 2, has_more: true, next_cursor: "next", limit: 25 } : undefined);
  expect(await screen.findByText(/Some versions on this page are unavailable/)).toBeTruthy();
  expect(screen.queryByText("No previous versions yet.")).toBeNull();
  expect(screen.getByRole("button", { name: "Next" }).hasAttribute("disabled")).toBe(false);
});

it("follows historical hash navigation while Research is mounted", async () => {
  location.hash = `Research/${packet.research_id}`;
  setup();
  await screen.findByRole("heading", { name: "Current Research version" });
  location.hash = `Research/${packet.research_id}/history/${"b".repeat(64)}`;
  fireEvent(window, new HashChangeEvent("hashchange"));
  expect(await screen.findByRole("heading", { name: "Previous Research version" })).toBeTruthy();
});

it("labels an explicitly opened current revision correctly without changing its packet", async () => {
  const id = "b".repeat(64);
  location.hash = `Research/${packet.research_id}/history/${id}`;
  setup(path => path.endsWith(id) ? { ...envelope(), is_current: true } : undefined);
  expect(await screen.findByRole("heading", { name: "Current Research version" })).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Previous Research version" })).toBeNull();
  expect(screen.getByText(/Read-only original packet/)).toBeTruthy();
  expect(screen.getByText("Original authority.")).toBeTruthy();
});

it("never displays an unavailable historical packet or raw diagnostics", async () => {
  const id = "b".repeat(64);
  location.hash = `Research/${packet.research_id}/history/${id}`;
  setup(path => path.endsWith(id) ? { error: { code: "RESEARCH_CORRUPTED_RESULT", message: "UNTRUSTED payload diagnostic" } } : undefined);
  expect(await screen.findByRole("alert")).toBeTruthy();
  expect(screen.queryByText("Original authority.")).toBeNull();
  expect(document.body.textContent).not.toMatch(/UNTRUSTED|RESEARCH_CORRUPTED_RESULT/);
});

it("keeps the loaded packet when reopening the already selected History entry", async () => {
  const id = "b".repeat(64);
  location.hash = `Research/${packet.research_id}/history/${id}`;
  setup(path => path.endsWith("/history") ? {
    revisions: [{ revision_id: id, assembled_at: packet.assembled_at, question: packet.question, output_language: "en", scope_count: 1, evidence_count: 1, intelligence_count: 0, status: "EVIDENCE_AVAILABLE" }],
    current_revision_id: "r", current_available: true, unavailable_count: 0, has_more: false, next_cursor: null, limit: 25,
  } : undefined);
  await screen.findByText("Original authority.");
  fireEvent.click(await screen.findByRole("button", { name: /Open previous version/ }));
  expect(screen.getByText("Original authority.")).toBeTruthy();
  expect(screen.queryByText("Verifying saved Research…")).toBeNull();
});
