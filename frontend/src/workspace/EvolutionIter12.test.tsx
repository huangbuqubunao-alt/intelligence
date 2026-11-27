import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function buildEvidenceList() {
  return [
    {
      evidence_id: "ev-1",
      artifact_id: "art-1",
      locator_type: "TIMED_SEGMENT",
      start_ms: 0,
      end_ms: 15000,
      start_line: null,
      end_line: null,
      source_language: "en",
      translation_target_language: "zh-CN",
      translated_language: "zh-CN",
      translated_excerpt: "第一段：状态机分离副作用。",
      original_excerpt: "State machines separate side effects.",
      lineage_kind: "CANONICAL_TRANSCRIPT",
      role: "PRIMARY",
      created_at: "2026-11-26T08:00:00Z",
    },
    {
      evidence_id: "ev-2",
      artifact_id: "art-1",
      locator_type: "TIMED_SEGMENT",
      start_ms: 15000,
      end_ms: 30000,
      start_line: null,
      end_line: null,
      source_language: "en",
      translation_target_language: "zh-CN",
      translated_language: "zh-CN",
      translated_excerpt: "第二段：参数校验。",
      original_excerpt: "Validate schemas on every tool boundary.",
      lineage_kind: "CANONICAL_TRANSCRIPT",
      role: "PRIMARY",
      created_at: "2026-11-26T08:00:00Z",
    },
    {
      evidence_id: "ev-3",
      artifact_id: "art-1",
      locator_type: "TIMED_SEGMENT",
      start_ms: 30000,
      end_ms: 45000,
      start_line: null,
      end_line: null,
      source_language: "en",
      translation_target_language: "zh-CN",
      translated_language: "zh-CN",
      translated_excerpt: "第三段：离线工作流。",
      original_excerpt: "Keep local ingestion offline.",
      lineage_kind: "CANONICAL_TRANSCRIPT",
      role: "PRIMARY",
      created_at: "2026-11-26T08:00:00Z",
    },
    {
      evidence_id: "ev-4",
      artifact_id: "art-1",
      locator_type: "TIMED_SEGMENT",
      start_ms: 45000,
      end_ms: 60000,
      start_line: null,
      end_line: null,
      source_language: "en",
      translation_target_language: "zh-CN",
      translated_language: "zh-CN",
      translated_excerpt: "第四段：崩溃恢复。",
      original_excerpt: "Checkpoint every transition to SQLite WAL.",
      lineage_kind: "CANONICAL_TRANSCRIPT",
      role: "PRIMARY",
      created_at: "2026-11-26T08:00:00Z",
    },
  ];
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

it("filters timed transcript segments, highlights <mark> hits, copies formatted quote, and penetrates collapsed evidence overflow on search", async () => {
  location.hash = "#Content/vidSearchDemo";
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) => {
      if (path === "/api/v1/videos/vidSearchDemo") {
        return jsonResponse({
          video: {
            video_id: "vidSearchDemo",
            title: "Durable State Machines",
            provider: "YOUTUBE",
            media_kind: "VIDEO",
            source_url: "https://www.youtube.com/watch?v=abcdefghijk",
            channel_id: "UC1",
            channel_name: "Atlas",
            processing_status: "READY",
            published_at: "2026-11-26T10:00:00Z",
            duration_seconds: 1200,
          },
          transcript: {
            status: "AVAILABLE",
            text: "Alpha intro.\nSQLite durability prevents partial state.",
            timed_segments: [
              { segment_id: "s1", start_ms: 0, end_ms: 10000, text: "Alpha intro line." },
              { segment_id: "s2", start_ms: 10000, end_ms: 25000, text: "SQLite durability prevents partial state." },
            ],
          },
          note: { v2: { status: "NOT_AVAILABLE" } },
          intelligence_result: { status: "NOT_AVAILABLE" },
          history: [],
        });
      }
      if (path.endsWith("/evidence")) {
        return jsonResponse({ evidence: buildEvidenceList() });
      }
      if (path.endsWith("/deep-analysis")) {
        return jsonResponse({
          deep_analysis: {
            status: {
              availability: "NOT_QUALIFIED",
              reason_code: "NO_QUALIFIED_MODEL",
              qualified: false,
              production_eligible: false,
              consent_required: false,
              routes: [],
            },
            result: null,
          },
        });
      }
      return jsonResponse({});
    }),
  );

  const user = userEvent.setup();
  const writeText = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue(undefined);
  render(<App />);

  await user.click(await screen.findByRole("button", { name: /查看原始字幕/ }));
  const transcriptSearchInput = await screen.findByRole("searchbox", { name: "搜索字幕正文" });
  await user.type(transcriptSearchInput, "SQLite");

  expect(await screen.findByText("命中 1 / 2 段")).toBeTruthy();
  expect(document.querySelectorAll("mark.reader-search-hit").length).toBeGreaterThanOrEqual(1);
  expect(screen.queryByText("Alpha intro line.")).toBeNull();

  await user.click(screen.getByRole("button", { name: /复制此段/ }));
  expect(writeText).toHaveBeenCalledWith(
    '> "SQLite durability prevents partial state."\n— 《Durable State Machines》 [0:10–0:25]',
  );

  // Switch to Evidence tab and search for #4 item (beyond initial 3-item fold)
  await user.click(screen.getByRole("tab", { name: /原话证据/ }));
  const evidenceSearchInput = await screen.findByRole("searchbox", { name: "搜索原话证据" });
  await user.type(evidenceSearchInput, "WAL");

  expect(await screen.findByText("命中 1 / 4 条")).toBeTruthy();
  expect(screen.getByText("第四段：崩溃恢复。")).toBeTruthy();
  expect(screen.queryByText("第一段：状态机分离副作用。")).toBeNull();
});

it("filters local Markdown document paragraphs in Source text drawer", async () => {
  location.hash = "#Content/localDocSearch";
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) => {
      if (path === "/api/v1/videos/localDocSearch") {
        return jsonResponse({
          video: {
            video_id: "localDocSearch",
            title: "local-notes.md",
            provider: "LOCAL",
            media_kind: "TEXT",
            channel_id: "local",
            channel_name: "Local",
            processing_status: "READY",
            imported_at: "2026-11-27T00:00:00Z",
          },
          transcript: {
            status: "AVAILABLE",
            text: "First design principle about determinism.\n\nSecond paragraph covering Obsidian backlinks.",
          },
          note: { v2: { status: "NOT_AVAILABLE" } },
          intelligence_result: { status: "NOT_AVAILABLE" },
          history: [],
        });
      }
      if (path.endsWith("/evidence")) return jsonResponse({ evidence: [] });
      if (path.endsWith("/deep-analysis")) {
        return jsonResponse({
          deep_analysis: {
            status: {
              availability: "NOT_QUALIFIED",
              reason_code: "NO_QUALIFIED_MODEL",
              qualified: false,
              production_eligible: false,
              consent_required: false,
              routes: [],
            },
            result: null,
          },
        });
      }
      return jsonResponse({});
    }),
  );

  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByRole("button", { name: /查看原始全文/ }));
  const docSearchInput = await screen.findByRole("searchbox", { name: "搜索文档原文" });
  await user.type(docSearchInput, "Obsidian");

  expect(await screen.findByText("命中 1 / 2 段")).toBeTruthy();
  expect(document.querySelector("mark.reader-search-hit")?.textContent).toBe("Obsidian");
  expect(screen.queryByText(/First design principle/)).toBeNull();
});
