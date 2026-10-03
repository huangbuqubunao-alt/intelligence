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
      : envelope());
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
  expect(screen.queryByText(/History|Compare versions|Diff/)).toBeNull();
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
  setup(path => path.endsWith(packet.research_id) ? { research: { ...envelope().research, packet: { ...packet, intelligence: ["supporting", "contradicting", "conditional", null].map((stance, index) => ({ intelligence_id: `i${index}`, revision_id: `r${index}`, content_id: "one", conclusion: "Source interpretation", claim_kind: "INFERENCE", state: "UPDATED", evidence_ids: ["durable"], stances: [stance] })) } } } : undefined);
  await screen.findAllByText("Source interpretation");
  expect(document.body.textContent).not.toMatch(/Supporting|Contradicting|Conditional|Relation not determined|Recorded state|INFERENCE|UPDATED/);
  expect(document.body.textContent).toContain("支持");
  expect(document.body.textContent).toContain("反驳");
  expect(document.body.textContent).toContain("附带条件");
});
