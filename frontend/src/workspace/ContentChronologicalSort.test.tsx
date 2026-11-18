import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { runViewTransition } from "./motion";

const okJson = (body: unknown, status = 200) =>
  Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);

beforeEach(() => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

describe("Content chronological ordering and long-video Shorts guard", () => {
  it("defaults Content list to newest-first, rescues >180s videos marked as short noise to #1, and lets user toggle to score order", async () => {
    location.hash = "#Content";

    const videosPayload = [
      {
        video_id: "vidHighOld",
        provider: "YOUTUBE",
        channel_id: "UColder",
        channel_name: "AI Builders",
        title: "Older High Score Deep Dive",
        published_at: "2026-11-12T08:00:00Z",
        processing_status: "READY",
        last_updated: "2026-11-12T09:00:00Z",
        duration_seconds: 1850,
        ai_brief: {
          video_id: "vidHighOld",
          headline_zh: "早期高分深度解析：工作流评测体系拆解",
          summary_zh: "系统拆解旧日期高分深度解析。",
          score: 9.2,
          score_reason_zh: "完整实战分析。",
          recommendation_tier: "MUST_WATCH",
          content_bucket: "DEEP_DIVE",
          is_short_noise: false,
          topics_zh: ["评测"],
          topic_cluster_zh: "AI Agent 工程架构",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
      {
        video_id: "vidMidRecent",
        provider: "YOUTUBE",
        channel_id: "UCrecent",
        channel_name: "OpenAI",
        title: "Yesterday Release Breakdown",
        published_at: "2026-11-17T06:00:00Z",
        processing_status: "READY",
        last_updated: "2026-11-17T08:00:00Z",
        duration_seconds: 1420,
        ai_brief: {
          video_id: "vidMidRecent",
          headline_zh: "昨日最新发布拆解：模型调用策略升级",
          summary_zh: "昨天发布的视频内容。",
          score: 7.8,
          score_reason_zh: "有新机制发布。",
          recommendation_tier: "WORTH_SKIMMING",
          content_bucket: "DEEP_DIVE",
          is_short_noise: false,
          topics_zh: ["模型发布"],
          topic_cluster_zh: "基础模型与基础设施",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
      {
        video_id: "localCourseNewest",
        provider: "LOCAL",
        media_kind: "VIDEO",
        format: ".mp4",
        channel_id: "local",
        channel_name: "Local",
        title: "1.简介 - AI 大模型全栈工程师_ev.mp4",
        imported_at: "2026-11-18T00:51:37Z",
        published_at: null,
        processing_status: "READY",
        last_updated: "2026-11-18T01:03:43Z",
        duration_seconds: 8236,
        ai_brief: {
          video_id: "localCourseNewest",
          headline_zh: "大模型全栈课程导学与环境配置说明",
          summary_zh: "课程开篇导学，虽被误标为短片但时长超过两小时。",
          score: 2.5,
          score_reason_zh: "误标低分测试样本。",
          recommendation_tier: "SKIP_NOISE",
          content_bucket: "SHORTS_PROMO",
          is_short_noise: true,
          topics_zh: ["课程导学"],
          topic_cluster_zh: "AI Agent 工程架构",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
      {
        video_id: "vidRealShort",
        provider: "YOUTUBE",
        channel_id: "UCshort",
        channel_name: "OpenAI",
        title: "Teaser Clip 42s #shorts",
        published_at: "2026-11-18T02:00:00Z",
        processing_status: "READY",
        last_updated: "2026-11-18T02:00:00Z",
        duration_seconds: 42,
        ai_brief: {
          video_id: "vidRealShort",
          headline_zh: "42 秒纯宣传预览短片",
          summary_zh: "真实短视频。",
          score: 2.0,
          score_reason_zh: "真实短片宣传。",
          recommendation_tier: "SKIP_NOISE",
          content_bucket: "SHORTS_PROMO",
          is_short_noise: true,
          topics_zh: ["短片"],
          topic_cluster_zh: "多模态生成与交互产品",
          product_opportunities_zh: [],
          business_opportunities_zh: [],
        },
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/videos")) {
          return okJson({ videos: videosPayload });
        }
        if (input.endsWith("/workspace-ai/hub")) {
          return okJson({
            items: videosPayload.map((v) => ({ video_id: v.video_id, ai_brief: v.ai_brief })),
            weekly_brief: null,
            topics: [],
          });
        }
        return okJson({});
      }),
    );

    const { container } = render(<App />);

    // Wait for newest course (rescued from mistakenly persisted is_short_noise on 8236s video) to render in the main list
    const localBtn = await screen.findByRole("button", {
      name: /1\.简介 - AI 大模型全栈工程师_ev\.mp4/,
    });
    expect(localBtn.closest("details")).toBeNull();

    // Primary list rows should be strictly ordered newest-first: localCourseNewest (11-18) -> vidMidRecent (11-17) -> vidHighOld (11-12)
    const getMainRowTitles = () =>
      Array.from(container.querySelectorAll(".content-row-shell[data-kb-video-id]"))
        .filter((el) => el.closest("details") === null)
        .map((el) => (el.querySelector(".content-media-copy > strong")?.textContent ?? "").trim());

    expect(getMainRowTitles()).toEqual([
      "1.简介 - AI 大模型全栈工程师_ev.mp4",
      "Yesterday Release Breakdown",
      "Older High Score Deep Dive",
    ]);

    // Real 42s Short stays folded inside the bottom Shorts drawer
    const shortsDrawer = container.querySelector("details.shorts-fold-drawer");
    expect(shortsDrawer).not.toBeNull();
    expect(shortsDrawer?.textContent).toContain("Teaser Clip 42s #shorts");
    expect(shortsDrawer?.textContent).not.toContain("1.简介 - AI 大模型全栈工程师_ev.mp4");

    // Sort toggle defaults to "最新优先" and can switch to "高分优先" and back
    const newestSortBtn = screen.getByRole("button", { name: "最新优先" });
    const scoreSortBtn = screen.getByRole("button", { name: "高分优先" });
    expect(newestSortBtn.getAttribute("aria-pressed")).toBe("true");
    expect(scoreSortBtn.getAttribute("aria-pressed")).toBe("false");

    fireEvent.click(scoreSortBtn);
    await waitFor(() => {
      expect(getMainRowTitles()).toEqual([
        "Older High Score Deep Dive",
        "Yesterday Release Breakdown",
        "1.简介 - AI 大模型全栈工程师_ev.mp4",
      ]);
    });

    fireEvent.click(newestSortBtn);
    await waitFor(() => {
      expect(getMainRowTitles()).toEqual([
        "1.简介 - AI 大模型全栈工程师_ev.mp4",
        "Yesterday Release Breakdown",
        "Older High Score Deep Dive",
      ]);
    });
  });

  it("renders clear actionable guidance on pending single-video YouTube import NEEDS_ATTENTION detail view and supports removing it", async () => {
    location.hash = "#Content/2hJkprFnzhY";
    let removed = false;

    const fetchMock = vi.fn((input: string, init?: RequestInit) => {
      if (input.endsWith("/sources/src-single-yt-1") && init?.method === "PATCH") {
        removed = true;
        return okJson({
          source: { source_id: "src-single-yt-1", enabled: false },
        });
      }
      if (input.endsWith("/videos/2hJkprFnzhY")) {
        return okJson({
          video: {
            video_id: "2hJkprFnzhY",
            provider: "YOUTUBE",
            work_kind: "DURABLE_CONTENT_IDENTITY",
            source_id: "src-single-yt-1",
            title: "https://www.youtube.com/watch?v=2hJkprFnzhY",
            source_url: "https://www.youtube.com/watch?v=2hJkprFnzhY",
            channel_id: null,
            channel_name: null,
            published_at: null,
            processing_status: "NEEDS_ATTENTION",
            last_updated: "2026-11-18T01:50:30Z",
          },
          transcript: { status: "NOT_AVAILABLE" },
          note: { v2: { status: "UNAVAILABLE" } },
          scoring: { status: "NOT_AVAILABLE" },
          intelligence_result: { status: "NOT_PROCESSED" },
          history: [],
        });
      }
      if (input.endsWith("/videos")) {
        return okJson({
          videos: removed
            ? []
            : [
                {
                  video_id: "2hJkprFnzhY",
                  provider: "YOUTUBE",
                  work_kind: "DURABLE_CONTENT_IDENTITY",
                  source_id: "src-single-yt-1",
                  title: "https://www.youtube.com/watch?v=2hJkprFnzhY",
                  source_url: "https://www.youtube.com/watch?v=2hJkprFnzhY",
                  channel_id: null,
                  channel_name: null,
                  published_at: null,
                  processing_status: "NEEDS_ATTENTION",
                  last_updated: "2026-11-18T01:50:30Z",
                },
              ],
        });
      }
      return okJson({});
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    // Wait for pending single-video detail screen
    expect(await screen.findByText(/YouTube 视频导入详情/)).toBeTruthy();
    // Should NOT show circular "请在内容页查看处理进度和需要处理的问题" inside #Content
    expect(screen.queryByText(/请在内容页查看处理进度和需要处理的问题/)).toBeNull();
    // Should explain plainly why YouTube link needs attention
    expect(screen.getByText("需要处理的原因")).toBeTruthy();
    expect(screen.getByText(/机器人验证限制/)).toBeTruthy();

    // Action buttons are clearly separated & usable
    expect(screen.getByRole("button", { name: "改用本地文件导入" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "重新尝试获取" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "在浏览器打开原视频" })).toBeTruthy();

    const removeBtn = screen.getByRole("button", { name: "从列表移除此记录" });
    fireEvent.click(removeBtn);

    await waitFor(() => {
      expect(removed).toBe(true);
      expect(location.hash).toBe("#Content");
    });
  });

  it("sorts Intelligence newest-first by effective_published_at with visible dates, and Topics newest-first by latest_published_at", async () => {
    location.hash = "#Intelligence";

    const intelligenceItems = [
      {
        status: "AVAILABLE",
        trusted: true,
        intelligence_id: "intel-oct10",
        claim_kind: "EVIDENCE_BACKED_STATEMENT",
        state: "NEW",
        effective_published_at: "2026-10-10T12:00:00Z",
        linked_topics: [{ topic_id: "t-agent", name: "AI Agent 与自动化架构" }],
        card: {
          core_conclusion: "十月本地课程旧洞察",
          user_relevant_information: ["旧内容。"],
          important_new_information: [],
          meaningful_details: [],
          source_id: "local-library",
          source_display_name: "Local library",
          source_url: null,
          video_id: "local-oct",
          video_title: "3. Agent.mp4",
          original_video_url: null,
          evidence_links: [],
        },
      },
      {
        status: "AVAILABLE",
        trusted: true,
        intelligence_id: "intel-nov18",
        claim_kind: "EVIDENCE_BACKED_STATEMENT",
        state: "NEW",
        effective_published_at: "2026-11-18T01:00:00Z",
        linked_topics: [{ topic_id: "t-agent", name: "AI Agent 与自动化架构" }],
        card: {
          core_conclusion: "十一月最新大模型课程洞察",
          user_relevant_information: ["最新内容。"],
          important_new_information: [],
          meaningful_details: [],
          source_id: "local-library",
          source_display_name: "Local library",
          source_url: null,
          video_id: "local-nov18",
          video_title: "1.简介 - AI 大模型全栈工程师_ev.mp4",
          original_video_url: null,
          evidence_links: [],
        },
      },
      {
        status: "AVAILABLE",
        trusted: true,
        intelligence_id: "intel-nov12",
        claim_kind: "EVIDENCE_BACKED_STATEMENT",
        state: "NEW",
        effective_published_at: "2026-11-12T10:00:00Z",
        linked_topics: [{ topic_id: "t-dev", name: "开发者工具与工程效能" }],
        card: {
          core_conclusion: "十一月十二日 OpenAI 洞察",
          user_relevant_information: ["中段内容。"],
          important_new_information: [],
          meaningful_details: [],
          source_id: "yt-openai",
          source_display_name: "OpenAI",
          source_url: null,
          video_id: "yt-nov12",
          video_title: "Nov 12 Release",
          original_video_url: null,
          evidence_links: [],
        },
      },
    ];

    const topicsItems = [
      {
        topic_id: "t-dev",
        name: "开发者工具与工程效能",
        pinned: true,
        lifecycle: "ACTIVE",
        current_state: "NEW",
        independence: "SINGLE_SOURCE",
        contributions: [],
        timeline: [],
        relations: [],
        ai_evolution: {
          video_count: 4,
          must_watch_count: 3,
          unread_count: 4,
          recent_7d_count: 4,
          avg_score: 8.5,
          latest_headline_zh: "工具链演化",
          latest_published_at: "2026-11-17T00:00:00Z",
          source_channels: ["OpenAI"],
          channel_breakdown: [],
        },
      },
      {
        topic_id: "t-agent",
        name: "AI Agent 与自动化架构",
        pinned: true,
        lifecycle: "ACTIVE",
        current_state: "NEW",
        independence: "MULTI_SOURCE",
        contributions: [],
        timeline: [],
        relations: [],
        ai_evolution: {
          video_count: 24,
          must_watch_count: 20,
          unread_count: 24,
          recent_7d_count: 10,
          avg_score: 8.7,
          latest_headline_zh: "全栈智能体最新实践",
          latest_published_at: "2026-11-18T01:00:00Z",
          source_channels: ["OpenAI", "本地内容库"],
          channel_breakdown: [],
        },
      },
    ];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/intelligence")) {
          return okJson({ intelligence: intelligenceItems, activity: [] });
        }
        if (input.endsWith("/saved-intelligence")) {
          return okJson({ saved: [] });
        }
        if (input.endsWith("/topics")) {
          return okJson({ topics: topicsItems });
        }
        return okJson({});
      }),
    );

    const { container } = render(<App />);

    expect(await screen.findByText("十一月最新大模型课程洞察")).toBeTruthy();
    const intelTitles = Array.from(container.querySelectorAll(".intel-row-title-btn")).map((el) =>
      (el.textContent ?? "").trim(),
    );
    expect(intelTitles).toEqual([
      "十一月最新大模型课程洞察",
      "十一月十二日 OpenAI 洞察",
      "十月本地课程旧洞察",
    ]);
    // Visible dates rendered on Intelligence rows
    expect(container.textContent).toContain("2026年11月18日");
    expect(container.textContent).toContain("2026年11月12日");
    expect(container.textContent).toContain("2026年10月10日");

    // Switch to Topics and verify chronological sorting + visible latest updated date
    fireEvent.click(screen.getByRole("button", { name: "主题" }));
    expect(await screen.findByText(/最近更新\s*2026年11月18日/)).toBeTruthy();
    const topicNames = Array.from(
      container.querySelectorAll(".content-media-list .content-media-copy > strong"),
    ).map((el) => (el.textContent ?? "").trim());
    expect(topicNames).toEqual(["AI Agent 与自动化架构", "开发者工具与工程效能"]);
  });

  it("skips document.startViewTransition on Chromium user agents and commits synchronously", () => {
    const originalUaDescriptor = Object.getOwnPropertyDescriptor(
      window.navigator,
      "userAgent",
    );
    const startViewTransition = vi.fn((cb: () => void) => {
      cb();
      return { finished: Promise.resolve() };
    });
    Object.defineProperty(document, "startViewTransition", {
      configurable: true,
      value: startViewTransition,
    });
    Object.defineProperty(window.navigator, "userAgent", {
      configurable: true,
      value:
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.8103.78 Safari/537.36",
    });

    try {
      let committed = 0;
      runViewTransition(() => {
        committed += 1;
      });
      expect(committed).toBe(1);
      expect(startViewTransition).not.toHaveBeenCalled();
    } finally {
      Reflect.deleteProperty(document, "startViewTransition");
      if (originalUaDescriptor) {
        Object.defineProperty(window.navigator, "userAgent", originalUaDescriptor);
      }
    }
  });
});

