import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

test("Topics detail renders Cross-source comparison cards and single opportunity heading without repetitive prefix", async () => {
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
  location.hash = "#Topics/topic-agents";

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/topics")) {
        return {
          ok: true,
          json: async () => ({
            topics: [
              {
                topic_id: "topic-agents",
                name: "AI Agent 工程架构",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "CONFIRMED",
                independence: "INDEPENDENT",
                contributions: [],
                timeline: [],
              },
            ],
          }),
        };
      }
      if (url.endsWith("/topics/topic-agents")) {
        return {
          ok: true,
          json: async () => ({
            topic: {
              topic_id: "topic-agents",
              name: "AI Agent 工程架构",
              pinned: true,
              lifecycle: "ACTIVE",
              current_state: "CONFIRMED",
              independence: "INDEPENDENT",
              contributions: [],
              timeline: [],
              relations: [],
              ai_evolution: {
                video_count: 3,
                must_watch_count: 3,
                unread_count: 2,
                recent_7d_count: 2,
                avg_score: 9.0,
                latest_headline_zh: "确定性状态机优于自由自治循环",
                latest_published_at: "2026-11-26T08:00:00Z",
                synthesis_zh:
                  "本专题综合 Atlas Agent Lab、极客架构演示室 共 2 个独立来源的 3 篇实测/解析（均分 9.0，其中 3 篇必看）。核心脉络聚焦「Atlas Agent Lab」提出的“确定性状态机优于自由自治循环”。",
                independence_summary_zh: "已汇聚 2 个独立来源交叉印证。",
                top_opportunities_zh: [
                  "本地知识库工作台与可审计引用工具链",
                  "面向个人研究者的免运维私有知识检索",
                ],
                source_perspectives: [
                  {
                    channel_name: "Atlas Agent Lab (Demo)",
                    video_id: "vidDemoAgt1",
                    title: "Deterministic State Machines for Production AI Agents",
                    headline_zh: "确定性状态机优于自由自治循环",
                    angle_zh: "用状态机约束工具权限边界并记录每步校验日志",
                    score: 9.4,
                  },
                  {
                    channel_name: "极客架构演示室（Demo）",
                    video_id: "bilibili-BV1DemoBili99",
                    title: "本地优先知识库与反幻觉证据链实战架构",
                    headline_zh: "双语混排字幕切分与反幻觉拒答",
                    angle_zh: "跨 B 站与 YouTube 资料建立时间戳原生证据链",
                    score: 8.9,
                  },
                ],
                source_channels: ["Atlas Agent Lab (Demo)", "极客架构演示室（Demo）"],
                channel_breakdown: [],
                related_topics: [],
                obsidian_markdown: "# AI Agent 工程架构",
                entries: [
                  {
                    video_id: "vidDemoAgt1",
                    title: "Deterministic State Machines for Production AI Agents",
                    channel_name: "Atlas Agent Lab (Demo)",
                    channel_key: "Atlas Agent Lab (Demo)",
                    published_at: "2026-11-26T08:00:00Z",
                    updated_at: "2026-11-26T08:00:00Z",
                    score: 9.4,
                    recommendation_tier: "MUST_WATCH",
                    headline_zh: "确定性状态机优于自由自治循环",
                    summary_zh: "用状态机约束工具权限边界。",
                    product_opportunities_zh: [],
                    business_opportunities_zh: [],
                  },
                ],
              },
            },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  await waitFor(() => {
    expect(screen.getByText("跨来源观点对照")).toBeTruthy();
  });
  expect(screen.getByText("用状态机约束工具权限边界并记录每步校验日志")).toBeTruthy();
  expect(screen.getByText("跨 B 站与 YouTube 资料建立时间戳原生证据链")).toBeTruthy();
  expect(screen.getByText("重点切入方向")).toBeTruthy();
  expect(screen.queryByText(/高优切口：/)).toBeNull();
  expect(screen.getByText("时间线")).toBeTruthy();
});

test("Empty Home displays 3-step quickstart and allows replaying onboarding after skipping", async () => {
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Home";

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/dashboard")) {
        return {
          ok: true,
          json: async () => ({
            intelligence: [],
            pinned_topics: [],
            weekly_v1: [],
            needs_attention: [],
            operations: { source_count: 0 },
          }),
        };
      }
      if (url.includes("/videos?limit=24")) {
        return { ok: true, json: async () => ({ videos: [] }) };
      }
      if (url.endsWith("/knowledge-delta")) {
        return {
          ok: true,
          json: async () => ({
            knowledge_delta: {
              window_start: "2026-11-19T00:00:00Z",
              window_end: "2026-11-26T00:00:00Z",
              timezone: "UTC",
              status: "available",
              detail_limit: 5,
              categories: [],
            },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  await waitFor(() => {
    expect(screen.getByText(/1\. 导入首条内容/)).toBeTruthy();
  });
  const replayBtn = screen.getByRole("button", { name: "重新查看新手引导" });
  fireEvent.click(replayBtn);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /1\. 核心流程/ })).toBeTruthy();
  });
});

test("Settings offers Replay onboarding button that opens FirstRunOnboarding", async () => {
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
  location.hash = "#Settings";

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/settings")) {
        return {
          ok: true,
          json: async () => ({
            general: {
              timezone: "Asia/Shanghai",
              output_language: "zh-CN",
              output_language_source: "EXPLICIT",
              output_language_updated_at: null,
            },
            providers: [],
            workspace_ai: {
              active_mode: "local_ollama",
              ollama_base_url: "http://127.0.0.1:11434",
              ollama_model: "qwen3.5:9b",
              ollama_reachable: true,
              installed_ollama_models: ["qwen3.5:9b"],
              cloud_provider: "bigmodel",
              cloud_base_url: "",
              cloud_model: "",
              cloud_key_configured: false,
            },
          }),
        };
      }
      if (url.endsWith("/settings/preferences")) {
        return { ok: true, json: async () => ({ active: [], history: [] }) };
      }
      if (url.endsWith("/settings/source-policy")) {
        return {
          ok: true,
          json: async () => ({
            policy: {
              initial_history_count: 5,
              per_run_max_new_videos: 5,
              focus_rules: [],
              ignore_rules: [],
              distillation_style: "BALANCED",
            },
          }),
        };
      }
      if (url.endsWith("/settings/resource-usage")) {
        return { ok: true, json: async () => ({ usage: [] }) };
      }
      if (url.endsWith("/youtube-auth")) {
        return { ok: true, json: async () => ({ status: "NOT_CONNECTED", cookie_count: 0 }) };
      }
      if (url.endsWith("/dashboard")) {
        return {
          ok: true,
          json: async () => ({
            demo_mode: true,
            intelligence: [
              {
                status: "AVAILABLE",
                trusted: true,
                intelligence_id: "intel-1",
                claim_kind: "SYSTEM_INFERENCE",
                state: "NEW",
                card: {
                  core_conclusion: "已验证洞察结论",
                  user_relevant_information: [],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "src-1",
                  source_display_name: "Atlas",
                  source_url: null,
                  video_id: "vid-1",
                  video_title: "Talk",
                  original_video_url: null,
                  evidence_links: [],
                },
              },
            ],
            pinned_topics: [],
            weekly_v1: [],
            needs_attention: [],
            operations: { source_count: 1 },
          }),
        };
      }
      if (url.includes("/videos?limit=24")) {
        return { ok: true, json: async () => ({ videos: [] }) };
      }
      if (url.endsWith("/knowledge-delta")) {
        return {
          ok: true,
          json: async () => ({
            knowledge_delta: {
              window_start: "2026-11-19T00:00:00Z",
              window_end: "2026-11-26T00:00:00Z",
              timezone: "UTC",
              status: "available",
              detail_limit: 5,
              categories: [],
            },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  const replayBtn = await screen.findByRole("button", { name: "重新查看新手引导" });
  fireEvent.click(replayBtn);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /1\. 核心流程/ })).toBeTruthy();
  });
});
