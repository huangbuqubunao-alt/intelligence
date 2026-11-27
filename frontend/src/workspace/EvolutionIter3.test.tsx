import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

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

test("Local markdown document reader suppresses video stage, hides undefined language, and uses Source text labels", async () => {
  location.hash = "#Content/vid-local-md";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.includes("/videos/vid-local-md/evidence")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      if (url.includes("/videos/vid-local-md")) {
        return {
          ok: true,
          json: async () => ({
            video: {
              video_id: "vid-local-md",
              channel_id: "local-ch",
              channel_name: "Local notes",
              title: "demo-architecture-notes.md",
              provider: "LOCAL",
              media_kind: "TEXT",
              format: ".md",
              source_language: "und",
              processing_status: "COMPLETE",
              ai_brief: {
                video_id: "vid-local-md",
                source_basis: "TRANSCRIPT",
                headline_zh: "本地架构笔记核心结论",
                summary_zh: "总结与可追踪证据链。",
                score: 8.8,
                recommendation_tier: "MUST_WATCH",
                topics_zh: ["架构设计"],
                product_opportunities_zh: [],
                business_opportunities_zh: [],
                obsidian_markdown: "# Demo",
              },
            },
            transcript: {
              status: "AVAILABLE",
              text: "# Demo note\nLocal-first knowledge base architecture.",
              timed_segments: [],
            },
            note: { v2: { status: "UNAVAILABLE" } },
            intelligence_result: { status: "UNAVAILABLE" },
            local_intelligence: { available: true },
            workspace_ai_capabilities: { ready: true, transcriber_ready: false },
            history: [],
          }),
        };
      }
      if (url.includes("/videos")) {
        return { ok: true, json: async () => ({ videos: [] }) };
      }
      if (url.endsWith("/capabilities/creator-following")) {
        return { ok: true, json: async () => ({ enabled: false }) };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  await waitFor(() => {
    expect(screen.getByText("demo-architecture-notes.md")).toBeTruthy();
  });

  expect(screen.queryByRole("button", { name: "YouTube" })).toBeNull();
  expect(screen.queryByText(/语言未知/)).toBeNull();
  expect(screen.getByRole("button", { name: /速跳 · 文档原文/ })).toBeTruthy();
  expect(screen.getByRole("button", { name: /查看原始全文/ })).toBeTruthy();
});

test("English Content Detail renders Re-distill AI brief without Chinese-only wording", async () => {
  localStorage.setItem("yia.ui-language", "en");
  location.hash = "#Content/vid-en-1";
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.includes("/videos/vid-en-1/evidence")) {
        return { ok: true, json: async () => ({ items: [] }) };
      }
      if (url.includes("/videos/vid-en-1")) {
        return {
          ok: true,
          json: async () => ({
            video: {
              video_id: "vid-en-1",
              channel_id: "ch-1",
              channel_name: "Systems Channel",
              title: "Reliable Tool Chains",
              provider: "YOUTUBE",
              media_kind: "VIDEO",
              format: "youtube",
              duration_seconds: 900,
              source_language: "en",
              processing_status: "COMPLETE",
              ai_brief: {
                video_id: "vid-en-1",
                source_basis: "TRANSCRIPT",
                headline_zh: "Tool chain reliability matters",
                summary_zh: "Deterministic execution wins.",
                score: 8.6,
                recommendation_tier: "MUST_WATCH",
                topics_zh: ["Agent"],
                product_opportunities_zh: [],
                business_opportunities_zh: [],
                obsidian_markdown: "# Reliable",
              },
            },
            transcript: {
              status: "AVAILABLE",
              text: "Deterministic execution wins.",
              timed_segments: [],
            },
            note: { v2: { status: "UNAVAILABLE" } },
            intelligence_result: { status: "UNAVAILABLE" },
            local_intelligence: { available: true },
            workspace_ai_capabilities: { ready: true, transcriber_ready: false },
            history: [],
          }),
        };
      }
      if (url.includes("/videos")) {
        return { ok: true, json: async () => ({ videos: [] }) };
      }
      if (url.endsWith("/capabilities/creator-following")) {
        return { ok: true, json: async () => ({ enabled: false }) };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  await waitFor(() => {
    expect(screen.getByRole("button", { name: /Re-distill AI brief/i })).toBeTruthy();
  });
  expect(screen.queryByRole("button", { name: /Re-distill AI Chinese brief/i })).toBeNull();
});
