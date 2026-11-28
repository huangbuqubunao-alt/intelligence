import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { UiLanguageProvider } from "./uiLanguage";
import { WorkspaceAiSettingsPanel } from "./WorkspaceAiWidgets";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

it.each([
  ["zh-CN", "local_ollama", "模式选择与月度成本参考", "¥0 边际费用 · 数据不出本机"],
  ["en", "cloud_byok", "Engine Mode & Cost Guide", "Pay-per-use · Est. ~$2–$6/mo"],
] as const)(
  "renders read-only cost transparency comparison (%s, %s) without triggering paid calls",
  async (lang, activeMode, heading, highlightPrice) => {
    localStorage.setItem("yia.ui-language", lang);
    const fetchMock = vi.fn((path: string, _init?: RequestInit) => {
      if (path.endsWith("/workspace-ai/config")) {
        return jsonResponse({
          active_mode: activeMode,
          ollama_model: "qwen3.5:9b",
          ollama_reachable: false,
          cloud_provider: "zhipu_bigmodel",
          cloud_model: "glm-4.5-air",
          cloud_key_configured: activeMode === "cloud_byok",
        });
      }
      return jsonResponse({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel id="ai-engine" />
      </UiLanguageProvider>,
    );

    expect(await screen.findByText(heading)).toBeTruthy();
    expect(screen.getByText(highlightPrice)).toBeTruthy();
    expect(screen.getByText(lang === "zh-CN" ? "当前生效" : "Active")).toBeTruthy();
    expect(
      fetchMock.mock.calls.every(
        ([, init]) => !init || !(init as RequestInit).method || (init as RequestInit).method === "GET",
      ),
    ).toBe(true);
  },
);

it("uses document text wording instead of transcript wording for un-distilled local Markdown docs", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = "#Content/local-md-1";

  const fetchMock = vi.fn((path: string) => {
    if (path === "/api/v1/videos/local-md-1") {
      return jsonResponse({
        video: {
          video_id: "local-md-1",
          title: "offline-architecture.md",
          provider: "LOCAL",
          media_kind: "TEXT",
          channel_id: "local",
          channel_name: "Local",
          processing_status: "READY",
          imported_at: "2026-11-27T00:00:00Z",
          last_updated: "2026-11-27T00:00:00Z",
          ai_brief: null,
        },
        transcript: {
          status: "AVAILABLE",
          text: "# Architecture\n\nKeep ingestion deterministic.",
          segments: [
            {
              segment_id: "seg1",
              start_ms: 0,
              end_ms: 0,
              text: "Keep ingestion deterministic.",
              source_lang: "en",
            },
          ],
        },
        note: { v2: { status: "NOT_AVAILABLE" } },
        intelligence_result: { status: "NOT_AVAILABLE" },
        history: [],
        workspace_ai_capabilities: { ready: true, transcriber_ready: false },
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
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(await screen.findByText("原文已就绪 · 待提炼洞察")).toBeTruthy();
  expect(
    screen.getByText("文档原文已准备完毕。点击下方按钮即可自动提炼中文总结、评分与核心洞察。"),
  ).toBeTruthy();
  expect(screen.queryByText(/原始字幕已准备完毕/)).toBeNull();
});
