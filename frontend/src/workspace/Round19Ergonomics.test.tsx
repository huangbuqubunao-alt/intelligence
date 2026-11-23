import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function okJson(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
  } as Response);
}

describe("Round 19 Workspace Ergonomics (R19-1, R19-2, R19-3)", () => {
  beforeEach(() => {
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
    delete document.documentElement.dataset.theme;
    location.hash = "";
  });

  it("R19-1: Cmd+K omits dynamic topic actions on empty query, and filters #Intelligence & scopes #Research on selection", async () => {
    location.hash = "#Home";
    const topics = [
      {
        topic_id: "tp-agent",
        name: "AI Agent 与自动化架构",
        pinned: true,
        lifecycle: "ACTIVE",
        current_state: "CONFIRMED",
        independence: "INDEPENDENT",
        contributions: [],
        timeline: [],
        ai_evolution: {
          video_count: 5,
          must_watch_count: 3,
          recent_7d_count: 2,
          avg_score: 9.2,
          latest_published_at: "2026-11-22T09:00:00Z",
          latest_headline_zh: "状态机约束让工具调用成功率大幅提升",
          source_channels: ["OpenAI", "Andrej Karpathy"],
          synthesis_zh: "多信源收敛到确定性编排与防幻觉门禁。",
        },
      },
      {
        topic_id: "tp-ops",
        name: "一人公司产品与增长",
        pinned: false,
        lifecycle: "ACTIVE",
        current_state: "CONFIRMED",
        independence: "INDEPENDENT",
        contributions: [],
        timeline: [],
        ai_evolution: {
          video_count: 2,
          must_watch_count: 1,
          recent_7d_count: 1,
          avg_score: 8.6,
          latest_published_at: "2026-11-20T09:00:00Z",
          latest_headline_zh: "垂直小工具适合自然搜索冷启动",
          source_channels: ["Greg Isenberg"],
        },
      },
    ];

    const videos = [
      {
        video_id: "vid-agent-1",
        provider: "YOUTUBE",
        channel_id: "ch-openai",
        channel_name: "OpenAI",
        title: "Production Agent Orchestration",
        published_at: "2026-11-22T09:00:00Z",
        processing_status: "ANALYZED",
        last_updated: "2026-11-22T09:00:00Z",
        duration_seconds: 1200,
        ai_brief: {
          headline_zh: "状态机约束工具调用",
          score: 9.2,
          recommendation_tier: "MUST_WATCH",
          content_bucket: "DEEP_DIVE",
          is_short_noise: false,
          starred: true,
          is_read: false,
          topic_cluster_zh: "AI Agent 与自动化架构",
        },
      },
    ];

    const intelligence = [
      {
        intelligence_id: "intel-agent-1",
        status: "AVAILABLE",
        trusted: true,
        claim_kind: "SUPPORTED_STATEMENT",
        state: "CONFIRMED",
        linked_topics: [{ topic_id: "tp-agent", name: "AI Agent 与自动化架构" }],
        card: {
          core_conclusion: "生产级 Agent 需用状态机约束高风险工具调用",
          user_relevant_information: ["状态机将多步工具调用失败率降低 60%"],
          important_new_information: ["在执行写入/支付工具前强制落盘审计与幂等校验。"],
          meaningful_details: ["状态转移显式声明前置约束"],
          source_id: "ch-openai",
          source_display_name: "OpenAI",
          source_url: "https://www.youtube.com/@OpenAI",
          video_id: "vid-agent-1",
          video_title: "Production Agent Orchestration",
          original_video_url: "https://www.youtube.com/watch?v=vid-agent-1",
          evidence_links: [],
        },
      },
      {
        intelligence_id: "intel-ops-1",
        status: "AVAILABLE",
        trusted: true,
        claim_kind: "SUPPORTED_STATEMENT",
        state: "CONFIRMED",
        linked_topics: [{ topic_id: "tp-ops", name: "一人公司产品与增长" }],
        card: {
          core_conclusion: "高意图搜索切入口比泛社交媒体投放留存更高",
          user_relevant_information: ["自然搜索冷启动飞轮具备更稳定的单月留存"],
          important_new_information: ["用单点高频痛点工具获取长尾自然流量并导入主工作台。"],
          meaningful_details: ["微工具无登录即可验证问题价值"],
          source_id: "ch-greg",
          source_display_name: "Greg Isenberg",
          source_url: "https://www.youtube.com/@GregIsenberg",
          video_id: "vid-ops-1",
          video_title: "Micro-SaaS SEO Loop",
          original_video_url: "https://www.youtube.com/watch?v=vid-ops-1",
          evidence_links: [],
        },
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/dashboard")) {
          return okJson({
            intelligence: [],
            pinned_topics: [],
            needs_attention: [],
            operations: { source_count: 1 },
          });
        }
        if (input.endsWith("/knowledge-delta")) {
          return okJson({
            knowledge_delta: {
              window_start: "2026-11-16T00:00:00Z",
              window_end: "2026-11-23T00:00:00Z",
              timezone: "Asia/Shanghai",
              status: "available",
              detail_limit: 2,
              categories: [],
            },
          });
        }
        if (input.endsWith("/videos")) return okJson({ videos });
        if (input.endsWith("/intelligence")) {
          return okJson({ intelligence, activity: [] });
        }
        if (input.endsWith("/saved-intelligence")) return okJson({ saved: [] });
        if (input.endsWith("/topics")) return okJson({ topics });
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: [],
            suggested_questions: [],
            scope_options: {
              starred_count: 1,
              channels: [{ key: "OpenAI", label: "OpenAI", count: 1 }],
              topic_clusters: [
                { name: "AI Agent 与自动化架构", count: 5 },
                { name: "一人公司产品与增长", count: 2 },
              ],
              videos: [],
            },
          });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        if (input.includes("/creator-following")) {
          return okJson({ available: false, reason_code: "DISABLED" });
        }
        return okJson({});
      }),
    );

    render(<App />);

    // Open Cmd+K with empty query -> dynamic topic filter/intel/ask actions remain hidden
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const dialog1 = await screen.findByRole("dialog", { name: /全局搜索与命令面板/ });
    const input1 = within(dialog1).getByRole("combobox");
    await waitFor(() =>
      expect(within(dialog1).queryByText("Production Agent Orchestration")).toBeTruthy(),
    );
    expect(within(dialog1).queryByRole("option", { name: /查看专题洞察：/ })).toBeNull();
    expect(within(dialog1).queryByRole("option", { name: /围绕专题追问：/ })).toBeNull();
    expect(within(dialog1).queryByRole("option", { name: /筛选专题内容：/ })).toBeNull();

    // Search "Agent" -> shows all three topic actions in exact rank priority order
    fireEvent.change(input1, { target: { value: "Agent" } });
    const intelOpt = await within(dialog1).findByRole("option", {
      name: /查看专题洞察：AI Agent 与自动化架构/,
    });
    const askOpt = await within(dialog1).findByRole("option", {
      name: /围绕专题追问：AI Agent 与自动化架构/,
    });
    expect(intelOpt).toBeTruthy();
    expect(askOpt).toBeTruthy();

    // Selecting "查看专题洞察" lands on #Intelligence filtered to that topic
    fireEvent.click(intelOpt);
    await waitFor(() => expect(location.hash).toBe("#Intelligence"));
    expect(
      await screen.findByText("生产级 Agent 需用状态机约束高风险工具调用"),
    ).toBeTruthy();
    expect(
      screen.queryByText("高意图搜索切入口比泛社交媒体投放留存更高"),
    ).toBeNull();

    // Re-open Cmd+K and pick "围绕专题追问：一人公司产品与增长" -> #Research topic scope applied
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const dialog2 = await screen.findByRole("dialog", { name: /全局搜索与命令面板/ });
    const input2 = within(dialog2).getByRole("combobox");
    fireEvent.change(input2, { target: { value: "一人公司" } });
    const askOpsOpt = await within(dialog2).findByRole("option", {
      name: /围绕专题追问：一人公司产品与增长/,
    });
    fireEvent.click(askOpsOpt);

    await waitFor(() => expect(location.hash).toBe("#Research"));
    const qaBox = (await screen.findByLabelText("跨视频提问")) as HTMLTextAreaElement;
    expect(qaBox.classList.contains("ai-research-textarea")).toBe(true);
    const topicSelect = await screen.findByLabelText("限定专题");
    expect((topicSelect as HTMLSelectElement).value).toBe("一人公司产品与增长");
  });

  it("R19-2: #Topics supports search, pinned filter, sort modes (pinned-first), no-match reset, and hides toolbar when empty", async () => {
    const sampleTopics = [
      {
        topic_id: "tp-b",
        name: "本地 Whisper 语音识别",
        pinned: false,
        lifecycle: "ACTIVE",
        current_state: "CONFIRMED",
        independence: "INDEPENDENT",
        contributions: [],
        timeline: [],
        ai_evolution: {
          video_count: 18,
          must_watch_count: 6,
          recent_7d_count: 3,
          avg_score: 8.1,
          latest_published_at: "2026-11-18T10:00:00Z",
          latest_headline_zh: "MLX Whisper 在 M 系列芯片转写速度大幅提升",
          source_channels: ["B站科技UP主"],
        },
      },
      {
        topic_id: "tp-a",
        name: "多模态视觉关键帧",
        pinned: true,
        lifecycle: "ACTIVE",
        current_state: "CONFIRMED",
        independence: "INDEPENDENT",
        contributions: [],
        timeline: [],
        ai_evolution: {
          video_count: 4,
          must_watch_count: 2,
          recent_7d_count: 2,
          avg_score: 7.9,
          latest_published_at: "2026-11-22T10:00:00Z",
          latest_headline_zh: "感知哈希去重减少 70% 重复视觉推理",
          source_channels: ["OpenAI"],
        },
      },
      {
        topic_id: "tp-c",
        name: "RAG 引用防幻觉评测",
        pinned: false,
        lifecycle: "ACTIVE",
        current_state: "CONFIRMED",
        independence: "INDEPENDENT",
        contributions: [],
        timeline: [],
        ai_evolution: {
          video_count: 9,
          must_watch_count: 7,
          recent_7d_count: 5,
          avg_score: 9.6,
          latest_published_at: "2026-11-21T10:00:00Z",
          latest_headline_zh: "32 例对抗评测验证 Fail-Closed 零伪造率",
          source_channels: ["Andrej Karpathy"],
        },
      },
    ];

    let topicPayload: typeof sampleTopics = sampleTopics;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/topics")) return okJson({ topics: topicPayload });
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0, offset: 0, limit: 25 });
        }
        if (input.includes("/creator-following")) {
          return okJson({ available: false, reason_code: "DISABLED" });
        }
        return okJson({});
      }),
    );

    location.hash = "#Topics";
    const { container } = render(<App />);

    expect(await screen.findByText("本地 Whisper 语音识别")).toBeTruthy();

    const readTopicOrder = () =>
      Array.from(container.querySelectorAll(".content-media-copy strong")).map(
        (el) => el.textContent ?? "",
      );

    // Default ("最近更新"): pinned first ("多模态视觉关键帧"), then 21st > 18th
    expect(readTopicOrder()).toEqual([
      "多模态视觉关键帧",
      "RAG 引用防幻觉评测",
      "本地 Whisper 语音识别",
    ]);

    // Switch to "内容最多": pinned first ("多模态视觉关键帧"), then 18 items > 9 items
    const sortGroup = screen.getByRole("group", { name: "主题排序" });
    fireEvent.click(within(sortGroup).getByRole("button", { name: "内容最多" }));
    expect(readTopicOrder()).toEqual([
      "多模态视觉关键帧",
      "本地 Whisper 语音识别",
      "RAG 引用防幻觉评测",
    ]);

    // Switch to "高分优先": pinned first, then 9.6 > 8.1
    fireEvent.click(within(sortGroup).getByRole("button", { name: "高分优先" }));
    expect(readTopicOrder()).toEqual([
      "多模态视觉关键帧",
      "RAG 引用防幻觉评测",
      "本地 Whisper 语音识别",
    ]);

    // Pinned-only filter toggle
    const pinnedBtn = screen.getByRole("button", { name: "仅看已置顶" });
    fireEvent.click(pinnedBtn);
    expect(pinnedBtn.getAttribute("aria-pressed")).toBe("true");
    expect(readTopicOrder()).toEqual(["多模态视觉关键帧"]);
    fireEvent.click(pinnedBtn);
    expect(readTopicOrder()).toHaveLength(3);

    // Search by channel name ("B站科技UP主") & takeaway ("Fail-Closed")
    const searchInput = screen.getByRole("searchbox", { name: "搜索主题" });
    fireEvent.change(searchInput, { target: { value: "B站科技UP主" } });
    expect(readTopicOrder()).toEqual(["本地 Whisper 语音识别"]);

    fireEvent.change(searchInput, { target: { value: "Fail-Closed" } });
    expect(readTopicOrder()).toEqual(["RAG 引用防幻觉评测"]);

    // No-match empty state + "重置筛选" restores full list
    fireEvent.change(searchInput, { target: { value: "完全不存在的关键词" } });
    expect(screen.getByText("没有匹配的主题。")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "重置筛选" }));
    expect(readTopicOrder()).toHaveLength(3);

    // When topics list is empty, hide filter toolbar and keep empty guidance
    cleanup();
    topicPayload = [];
    render(<App />);
    expect(await screen.findByText("暂无主题。")).toBeTruthy();
    expect(screen.queryByRole("searchbox", { name: "搜索主题" })).toBeNull();
    expect(screen.queryByRole("group", { name: "主题排序" })).toBeNull();
  });
});
