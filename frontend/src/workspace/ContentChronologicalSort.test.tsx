import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

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
});
