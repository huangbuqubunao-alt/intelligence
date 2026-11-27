import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

test.each(["zh-CN", "en"] as const)(
  "Topics Compare consensus & divergence button hands off multi-video comparison draft to Research without auto-asking (%s)",
  async (lang) => {
    localStorage.setItem("yia.ui-language", lang);
    location.hash = "#Topics/topic-agents";
    const askCalls: unknown[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/topics")) {
          return {
            ok: true,
            json: async () => ({
              topics: [
                {
                  topic_id: "topic-agents",
                  name: "AI Agent Architecture",
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
                name: "AI Agent Architecture",
                pinned: true,
                lifecycle: "ACTIVE",
                current_state: "CONFIRMED",
                independence: "INDEPENDENT",
                contributions: [],
                timeline: [],
                relations: [],
                ai_evolution: {
                  video_count: 2,
                  must_watch_count: 2,
                  unread_count: 1,
                  recent_7d_count: 2,
                  avg_score: 9.0,
                  latest_headline_zh: "State machines outperform loose loops",
                  latest_published_at: "2026-11-26T08:00:00Z",
                  synthesis_zh: "Synthesis across 2 independent sources.",
                  independence_summary_zh: "Cross-referenced across 2 sources.",
                  top_opportunities_zh: [],
                  source_perspectives: [
                    {
                      channel_name: "Atlas Lab",
                      video_id: "vid-1",
                      title: "State Machines",
                      headline_zh: "Use state machines",
                      angle_zh: "Constraint boundaries first",
                      score: 9.4,
                    },
                    {
                      channel_name: "Foundry",
                      video_id: "vid-2",
                      title: "Local Provenance",
                      headline_zh: "Keep hashes local",
                      angle_zh: "Deterministic SQLite audit logs",
                      score: 8.8,
                    },
                  ],
                  source_channels: ["Atlas Lab", "Foundry"],
                  channel_breakdown: [],
                  related_topics: [],
                  obsidian_markdown: "# AI Agent Architecture",
                  entries: [
                    {
                      video_id: "vid-1",
                      title: "State Machines",
                      channel_name: "Atlas Lab",
                      published_at: "2026-11-26T08:00:00Z",
                      score: 9.4,
                      recommendation_tier: "MUST_WATCH",
                      source_basis: "TRANSCRIPT",
                      headline_zh: "Use state machines",
                      summary_zh: "Constraint boundaries first",
                      product_opportunities_zh: [],
                      business_opportunities_zh: [],
                    },
                  ],
                },
              },
            }),
          };
        }
        if (url.endsWith("/workspace-ai/research/sessions")) {
          return {
            ok: true,
            json: async () => ({
              sessions: [],
              suggested_questions: [],
              scope_options: {
                starred_count: 0,
                channels: [
                  { key: "Atlas Lab", label: "Atlas Lab", count: 1 },
                  { key: "Foundry", label: "Foundry", count: 1 },
                ],
                topic_clusters: [{ name: "AI Agent Architecture", count: 2 }],
                videos: [
                  { video_id: "vid-1", title: "State Machines", channel_name: "Atlas Lab", score: 9.4 },
                  { video_id: "vid-2", title: "Local Provenance", channel_name: "Foundry", score: 8.8 },
                ],
              },
            }),
          };
        }
        if (url.endsWith("/workspace-ai/research/ask")) {
          askCalls.push(init?.body);
          return { ok: true, json: async () => ({}) };
        }
        if (url.startsWith("/api/v1/research")) {
          return { ok: true, json: async () => ({ research: [], total: 0, limit: 20, offset: 0 }) };
        }
        return { ok: true, json: async () => ({}) };
      }),
    );

    render(<App />);
    const compareBtn = await screen.findByRole("button", {
      name: lang === "zh-CN" ? /对比共识与分歧 \(2\)/ : /Compare consensus & divergence \(2\)/,
    });
    fireEvent.click(compareBtn);

    await waitFor(() => {
      expect(location.hash).toBe("#Research");
    });

    const input = (await screen.findByRole("textbox", {
      name: lang === "zh-CN" ? "跨视频提问" : "Ask across videos",
    })) as HTMLTextAreaElement;
    expect(input.value).toContain("AI Agent Architecture");
    expect(
      screen.getByText(
        lang === "zh-CN" ? /已锁定 2 篇指定源视频/ : /Scoped to 2 selected videos/,
      ),
    ).toBeTruthy();
    expect(askCalls).toHaveLength(0);
  },
);

test("Research contextual follow-up chips lock active scope and populate editable input without auto-submitting", async () => {
  location.hash = "#Research";
  const askCalls: unknown[] = [];

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/workspace-ai/research/sessions")) {
        return {
          ok: true,
          json: async () => ({
            sessions: [
              {
                session_id: "sess-iter7",
                question: "本地工具如何保证可审计性？",
                answer_status: "GROUNDED",
                source_integrity_status: "VERIFIED",
                fact_verification_state: "SUPPORTED",
                scope_label_zh: "全部可核验材料",
                pinned: false,
                answer_zh: "通过本地 SQLite 原文快照与时间戳引文锁定依据 [E1][E2]。",
                key_takeaways_zh: ["原文先落盘", "逐条绑定引用"],
                action_items_zh: [],
                citations: [
                  {
                    ref_label: "E1",
                    video_id: "vid-1",
                    video_title: "State Machines",
                    channel_name: "Atlas Lab",
                    evidence_id: "ev-1",
                    start_ms: 1000,
                    end_ms: 5000,
                    timestamp_label: "00:01",
                    excerpt: "Save raw transcript with checksum first.",
                  },
                  {
                    ref_label: "E2",
                    video_id: "vid-2",
                    video_title: "Local Provenance",
                    channel_name: "Foundry",
                    evidence_id: "ev-2",
                    start_ms: 2000,
                    end_ms: 6000,
                    timestamp_label: "00:02",
                    excerpt: "Verify every claim against saved spans.",
                  },
                ],
                obsidian_markdown: "# Q&A",
                provider: "ollama",
                model: "qwen3.5:9b",
                created_at: "2026-11-27T00:00:00Z",
              },
            ],
            suggested_questions: [],
            scope_options: {
              starred_count: 0,
              channels: [{ key: "Atlas Lab", label: "Atlas Lab", count: 1 }],
              topic_clusters: [],
              videos: [
                { video_id: "vid-1", title: "State Machines", channel_name: "Atlas Lab", score: 9.4 },
                { video_id: "vid-2", title: "Local Provenance", channel_name: "Foundry", score: 8.8 },
              ],
            },
          }),
        };
      }
      if (url.endsWith("/workspace-ai/research/ask")) {
        askCalls.push(init?.body);
        return { ok: true, json: async () => ({}) };
      }
      if (url.startsWith("/api/v1/research")) {
        return { ok: true, json: async () => ({ research: [], total: 0, limit: 20, offset: 0 }) };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  const followUpChip = await screen.findByRole("button", {
    name: "对比不同来源的核心分歧与边界条件",
  });
  fireEvent.click(followUpChip);

  const input = screen.getByRole("textbox", { name: "跨视频提问" }) as HTMLTextAreaElement;
  expect(input.value).toBe("对比不同来源的核心分歧与边界条件");
  expect(screen.getByText(/已锁定 2 篇指定源视频/)).toBeTruthy();
  expect(screen.getByText(/已锁定当前来源范围并填入追问/)).toBeTruthy();
  expect(askCalls).toHaveLength(0);
});
