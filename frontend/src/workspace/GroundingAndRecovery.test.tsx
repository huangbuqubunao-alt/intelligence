import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { KnowledgeDelta, KnowledgeDeltaProjection } from "./KnowledgeDelta";
import { WorkspaceAiResearchPanel } from "./WorkspaceAiWidgets";
import { UiLanguageProvider } from "./uiLanguage";

const okJson = (body: unknown) => ({
  ok: true,
  status: 200,
  json: async () => body,
});

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

it("renders honest refusal badge, separated related excerpts, and synthetic replay pill on Research Q&A", async () => {
  const fetchMock = vi.fn(async (input: string) => {
    if (input.endsWith("/workspace-ai/research/sessions")) {
      return okJson({
        sessions: [
          {
            session_id: "qa-refused-1",
            question: "语料里提到 2026 Q3 净利润吗？",
            answer_status: "REFUSED_INSUFFICIENT_EVIDENCE",
            refused: true,
            refusal_reason_zh: "候选片段仅讨论状态机与引用校验，未包含财务数据。",
            answer_zh: "证据不足，无法基于当前资料库可靠回答：候选片段仅讨论状态机与引用校验，未包含财务数据。",
            key_takeaways_zh: [],
            action_items_zh: [],
            citations: [],
            related_excerpts: [
              {
                ref_label: "E1",
                video_id: "vidDemoAgt1",
                video_title: "Deterministic State Machines",
                channel_name: "Atlas Agent Lab (Demo)",
                evidence_id: "ev-rel-1",
                start_ms: 0,
                end_ms: 12000,
                timestamp_label: "00:00",
                excerpt: "Production agents use SQLite checkpoints.",
              },
            ],
            video_count: 1,
            scope_label_zh: "",
            pinned: false,
            provider: "demo-replay",
            model: "synthetic-showcase-v1",
            obsidian_markdown: "# 拒答记录",
            created_at: "2026-11-20T12:00:00Z",
          },
        ],
        suggested_questions: [],
        scope_options: { channels: [], topic_clusters: [], videos: [], starred_count: 0 },
      });
    }
    return okJson({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(
    <UiLanguageProvider>
      <WorkspaceAiResearchPanel onOpen={vi.fn()} />
    </UiLanguageProvider>,
  );

  expect(await screen.findByText("证据不足 · 已诚实拒答")).toBeTruthy();
  expect(screen.getByText("离线合成样例回放")).toBeTruthy();
  expect(
    screen.getByText("相关原始片段（仅供参考查阅，未作为支持结论的引用）"),
  ).toBeTruthy();
  expect(screen.queryByText("可验证原话时间轴出处（点击直达对应视频与证据）")).toBeNull();
});

it("surfaces plain-language C4 failure reasons and local recovery CTA even when retry is disabled", async () => {
  location.hash = "#Content/vidFail01";
  const fetchMock = vi.fn(async (input: string) => {
    if (input === "/api/v1/local/native/capability") {
      return okJson({ capability: { available: false } });
    }
    if (input === "/api/v1/videos/vidFail01") {
      return okJson({
        video: {
          video_id: "vidFail01",
          provider: "YOUTUBE",
          title: "Restricted Capture Video",
          channel_id: "UC1111111111111111111111",
          channel_name: "Channel A",
          source_id: "src-fail-1",
          retry_allowed: false,
          last_error_code: "CAPABILITY_UNAVAILABLE",
          source_url: "https://www.youtube.com/watch?v=vidFail01",
          published_at: "2026-11-19T10:00:00Z",
          processing_status: "FAILED",
          last_updated: "2026-11-19T10:05:00Z",
        },
        transcript: { status: "UNAVAILABLE" },
        note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
        intelligence_result: { status: "NOT_PROCESSED" },
        history: [],
      });
    }
    if (input.endsWith("/evidence") || input.endsWith("/deep-analysis")) {
      return okJson({ evidence: [], deep_analysis: null });
    }
    return okJson({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(
    await screen.findByText(/当前来源抓取能力受限（例如平台要求登录验证或未开放公开字幕）/),
  ).toBeTruthy();
  const importFallbackBtn = screen.getByRole("button", { name: "导入本地文件替代" });
  expect(importFallbackBtn).toBeTruthy();
  expect((screen.getByRole("button", { name: "重试" }) as HTMLButtonElement).disabled).toBe(true);

  fireEvent.click(importFallbackBtn);
  expect(await screen.findByRole("dialog", { name: "添加本地文件" })).toBeTruthy();
});

it("hides zero-count KnowledgeDelta KPI tiles while preserving non-zero and Unavailable metrics", async () => {
  const delta: KnowledgeDeltaProjection = {
    window_start: "2026-11-13T00:00:00Z",
    window_end: "2026-11-20T00:00:00Z",
    timezone: "Asia/Shanghai",
    status: "partial",
    detail_limit: 2,
    categories: [
      { kind: "content_completed", status: "available", count: 3, items: [] },
      { kind: "intelligence_added", status: "available", count: 0, items: [] },
      { kind: "intelligence_revised", status: "available", count: 0, items: [] },
      { kind: "topic_updated", status: "unavailable", count: null, items: [] },
      { kind: "source_health", status: "available", count: 0, items: [] },
    ],
  };
  vi.stubGlobal("fetch", vi.fn(async () => okJson({ knowledge_delta: delta })));

  render(
    <UiLanguageProvider>
      <KnowledgeDelta refresh={0} onOpen={vi.fn()} />
    </UiLanguageProvider>,
  );

  const region = await screen.findByRole("region", { name: "最近 7 天发生了什么变化？" });
  expect(within(region).getByText("已完成内容")).toBeTruthy();
  expect(within(region).getByText("不可用")).toBeTruthy();
  expect(within(region).queryByText("新增洞察")).toBeNull();
  expect(within(region).queryByText("洞察修订")).toBeNull();
  expect(within(region).queryByText("来源健康变化")).toBeNull();
});

it("renders covered_sources strip and Markdown TEXT_RANGE paragraph locators without 00:00", async () => {
  const fetchMock = vi.fn(async (input: string) => {
    if (input.endsWith("/workspace-ai/research/sessions")) {
      return okJson({
        sessions: [
          {
            session_id: "qa-cross-md-1",
            question: "对比视频原话与本地 Markdown 架构笔记的证据机制",
            answer_status: "GROUNDED",
            refused: false,
            refusal_reason_zh: "",
            answer_zh: "视频采用时间轴定位 [E1]，本地 Markdown 采用字符起止区间定位 [E2]。",
            key_takeaways_zh: ["统一绑定核心库 evidence_id"],
            action_items_zh: ["同时核验两类原文引用"],
            covered_source_count: 2,
            covered_sources: [
              {
                video_id: "vidYT01",
                title: "State Machines Talk",
                provider: "YOUTUBE",
                channel_name: "Alpha Lab",
                locator_type: "TIME_RANGE",
              },
              {
                video_id: "local-md-01",
                title: "architecture-notes.md",
                provider: "LOCAL",
                channel_name: "本地实战课",
                locator_type: "TEXT_RANGE",
              },
            ],
            citations: [
              {
                ref_label: "E1",
                video_id: "vidYT01",
                video_title: "State Machines Talk",
                channel_name: "Alpha Lab",
                evidence_id: "ev-yt-1",
                locator_type: "TIME_RANGE",
                start_ms: 10000,
                end_ms: 22000,
                timestamp_label: "00:10",
                excerpt: "Checkpoints prevent silent failures.",
              },
              {
                ref_label: "E2",
                video_id: "local-md-01",
                video_title: "architecture-notes.md",
                channel_name: "本地实战课",
                evidence_id: "ev-md-2",
                locator_type: "TEXT_RANGE",
                paragraph_index: 2,
                start_offset: 48,
                end_offset: 142,
                start_ms: null,
                end_ms: null,
                timestamp_label: "P2 (48–142)",
                excerpt: "Persist TEXT_RANGE offsets before model distillation.",
              },
            ],
            video_count: 2,
            scope_label_zh: "",
            pinned: false,
            provider: "ollama",
            model: "qwen3.5:9b",
            obsidian_markdown: "# 跨源对比",
            created_at: "2026-11-20T13:00:00Z",
          },
        ],
        suggested_questions: [],
        scope_options: { channels: [], topic_clusters: [], videos: [], starred_count: 0 },
      });
    }
    return okJson({});
  });
  vi.stubGlobal("fetch", fetchMock);

  render(
    <UiLanguageProvider>
      <WorkspaceAiResearchPanel onOpen={vi.fn()} />
    </UiLanguageProvider>,
  );

  expect(await screen.findByText(/本次检索覆盖 2 份可核验材料/)).toBeTruthy();
  const strip = screen.getByRole("group", { name: "本次检索覆盖的可核验材料" });
  expect(within(strip).getByText("State Machines Talk")).toBeTruthy();
  expect(within(strip).getByText("architecture-notes.md")).toBeTruthy();
  expect(within(strip).getByText("文档")).toBeTruthy();
  expect(screen.getByText("可验证原话出处（时间戳 / 段落定位，点击直达原文）")).toBeTruthy();
  expect(screen.getByText("P2 (48–142)")).toBeTruthy();
  expect(screen.queryByText("00:00")).toBeNull();
});
