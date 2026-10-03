import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { Research } from "./Research";
import { ResearchDiff } from "./ResearchDiff";
import { ResearchDiffProjection } from "./ResearchTypes";
import { UiLanguageProvider } from "./uiLanguage";

const research = "a".repeat(64), base = "b".repeat(64), target = "c".repeat(64);
const empty = { added: [], removed: [], unchanged_count: 0 };
const diff: ResearchDiffProjection = {
  contract: "research-diff-v1", packet_contract: "research-lite-v1", research_id: research,
  question: "What evidence?", output_language: "en", base: { revision_id: base, execution_number: 1, assembled_at: "2026-10-03T08:00:00Z", scope: [{ content_id: "one", title: "Original title" }] },
  target: { revision_id: target, execution_number: 2, assembled_at: "2026-10-03T08:00:00Z", scope: [{ content_id: "one", title: "New title" }] },
  summary: { added: 0, removed: 0, changed: 0 }, no_material_changes: true,
  content: empty, evidence: empty, interpretations: empty, packet_changes: [], complete: true,
  content_limit_per_side: 20, evidence_limit_per_side: 24, interpretation_limit_per_side: 6,
};
function setup(data: object = { diff }, language = "en") {
  localStorage.setItem("yia.ui-language", language);
  const request = vi.fn(async (path: string) => ({ ok: !("error" in data), json: async () => data }));
  vi.stubGlobal("fetch", request);
  const onOpen = vi.fn(), onRevision = vi.fn(), onClose = vi.fn();
  render(<UiLanguageProvider><ResearchDiff researchId={research} baseId={base} targetId={target} onOpen={onOpen} onRevision={onRevision} onClose={onClose} /></UiLanguageProvider>);
  return { request, onOpen, onRevision, onClose };
}
beforeEach(() => { location.hash = "Research"; localStorage.setItem("yia.ui-language", "en"); });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

it.each(["en", "zh-CN"])("shows directional context and no-change in %s", async language => {
  const { request, onRevision, onClose } = setup({ diff }, language);
  const text = (en: string, zh: string) => language === "en" ? en : zh;
  await screen.findByText(text("No material changes", "无实质变化"));
  expect(screen.getByText(text("Base version", "基础版本"))).toBeTruthy();
  expect(screen.getByText(text("Target version", "目标版本"))).toBeTruthy();
  expect(request.mock.calls[0][0]).toContain(`base_revision=${base}&target_revision=${target}`);
  fireEvent.click(screen.getByRole("button", { name: text("Open base version", "打开基础版本") }));
  expect(onRevision).toHaveBeenCalledWith(base);
  fireEvent.click(screen.getByRole("button", { name: text("Close comparison", "关闭对比") }));
  expect(onClose).toHaveBeenCalled();
  if (language === "zh-CN") expect(document.body.textContent).not.toMatch(/No material|Base version|Target version|VERIFIED/);
});

it("traces each side's frozen Evidence", async () => {
  const evidence = { id: "evidence:old", content_id: "one", title: "Historical title", evidence_id: "old", excerpt: "Historical source.", start_ms: 1, end_ms: 2, source_language: "en", lineage_kind: "ORIGINAL_TRANSCRIPT" };
  const { onOpen } = setup({ diff: { ...diff, no_material_changes: false, summary: { added: 1, removed: 1, changed: 0 }, evidence: { added: [{ ...evidence, id: "evidence:new", evidence_id: "new", title: "Target title", excerpt: "Target source." }], removed: [evidence], unchanged_count: 0 } } });
  await screen.findByText("Historical source.");
  const buttons = screen.getAllByRole("button", { name: "Open Content and Evidence" });
  fireEvent.click(buttons[0]); fireEvent.click(buttons[1]);
  expect(onOpen.mock.calls).toEqual([["content", "one", "new"], ["content", "one", "old"]]);
});

it.each(["RESEARCH_DIFF_BASE_NOT_FOUND", "RESEARCH_DIFF_TARGET_NOT_FOUND", "RESEARCH_DIFF_WRONG_RESEARCH", "RESEARCH_DIFF_UNTRUSTED_REVISION", "RESEARCH_DIFF_INCOMPATIBLE_CONTRACT", "RESEARCH_DIFF_INVALID_REQUEST"])("localizes %s", async code => {
  setup({ error: { code, message: "PRIVATE backend English" } }, "zh-CN");
  await screen.findByRole("alert");
  expect(document.body.textContent).not.toMatch(/PRIVATE|RESEARCH_DIFF_|unavailable|Research contract/);
  expect(screen.queryByText("What evidence?")).toBeNull();
});

it("rejects a response with mismatched direction", async () => {
  setup({ diff: { ...diff, base: diff.target } });
  await screen.findByRole("alert");
  expect(screen.queryByText("What evidence?")).toBeNull();
});

it.each(["en", "zh-CN"])("localizes metadata and interpretation qualifications in %s", async language => {
  setup({ diff: { ...diff, no_material_changes: false, interpretations: { added: [{ id: "i", content_id: "one", title: "Source", intelligence_id: "i", revision_id: "recorded-r", conclusion: "Original interpretation", claim_kind: "SYSTEM_INFERENCE", state: "UPDATED", citations: [{ evidence_id: "e", stance: "contradicting" }] }], removed: [], unchanged_count: 0 }, packet_changes: [
    { id: "status", field: "material_status", base: "INSUFFICIENT_MATERIAL", target: "EVIDENCE_AVAILABLE" },
    { id: "bound", field: "retrieval_truncated", base: false, target: true },
    { id: "flags", field: "unresolved", base: ["NO_SYNTHESIS", "LEXICAL_RETRIEVAL"], target: ["BOUNDED_PACKET", "NO_MATCHING_EVIDENCE"] },
  ] } }, language);
  await screen.findByText("Original interpretation");
  expect(document.body.textContent).not.toMatch(/SYSTEM_INFERENCE|UPDATED|INSUFFICIENT_MATERIAL|EVIDENCE_AVAILABLE|NO_SYNTHESIS|BOUNDED_PACKET/);
  if (language === "zh-CN") expect(document.body.textContent).not.toMatch(/Material status|Packet limitations|Recorded interpretations|No model synthesis|Word matching only|Yes|No matching/);
  else expect(document.body.textContent).not.toMatch(/[\u3400-\u9fff]/);
});

function researchSetup(revisions: string[], historical = false) {
  location.hash = `Research/${research}${historical ? `/history/${base}` : ""}`;
  const request = vi.fn(async (path: string) => ({ ok: true, json: async () => path.includes("/diff?") ? { diff } : path.endsWith("/history") ? {
    revisions: revisions.map(revision_id => ({ revision_id, assembled_at: diff.base.assembled_at, question: diff.question, output_language: "en", scope_count: 1, evidence_count: 0, intelligence_count: 0, status: "INSUFFICIENT_MATERIAL" })), current_revision_id: target, current_available: true, unavailable_count: 0, has_more: false, next_cursor: null, limit: 25,
  } : path.endsWith("/research") ? { research: [], total: 0, offset: 0, limit: 25 } : {
    research: { result_identity: historical ? base : target, provenance_status: "VERIFIED", packet: { research_id: research, question: diff.question, assembled_at: diff.base.assembled_at, output_language: "en", scope: diff.base.scope, material_status: "INSUFFICIENT_MATERIAL", intelligence: [], evidence: [], evidence_candidates: 0, intelligence_candidates: 0, retrieval_truncated: false } }, is_current: !historical,
  } }));
  vi.stubGlobal("fetch", request);
  render(<UiLanguageProvider><Research onOpen={vi.fn()} /></UiLanguageProvider>);
  return request;
}
it("has no previous compare for one revision", async () => {
  researchSetup([]);
  await screen.findByText("No previous versions yet.");
  expect(screen.queryByRole("button", { name: "Compare with previous" })).toBeNull();
});
it("compares current with previous using explicit older→current identities", async () => {
  const request = researchSetup([base]);
  fireEvent.click(await screen.findByRole("button", { name: "Compare with previous" }));
  await screen.findByText("No material changes");
  expect(location.hash).toBe(`#Research/${research}/diff/${base}/${target}`);
  expect(request.mock.calls.some(([path]) => path.includes(`base_revision=${base}&target_revision=${target}`))).toBe(true);
});
it("compares historical with current and opens original base", async () => {
  researchSetup([base], true);
  fireEvent.click(await screen.findByRole("button", { name: "Compare with current" }));
  await screen.findByText("No material changes");
  fireEvent.click(screen.getByRole("button", { name: "Open base version" }));
  await screen.findByRole("heading", { name: "Previous Research version" });
  expect(location.hash).toBe(`#Research/${research}/history/${base}`);
});
