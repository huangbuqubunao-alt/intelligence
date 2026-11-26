import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
  location.hash = "#Home";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

test("Home renders Priority Reading Queue filtering out Shorts noise and marks items read in 1 click", async () => {
  const postedUrls: string[] = [];
  let markedRead = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, options?: RequestInit) => {
      if (url.includes("/workspace-ai/videos/vid-top/curation") && options?.method === "POST") {
        postedUrls.push(url);
        markedRead = true;
        return { ok: true, json: async () => ({ ok: true }) };
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
                  core_conclusion: "状态机约束工具调用可显著提升可靠性。",
                  user_relevant_information: [],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "src-1",
                  source_display_name: "Atlas Agent Lab",
                  source_url: null,
                  video_id: "vid-top",
                  video_title: "State Machines Talk",
                  original_video_url: null,
                  evidence_links: [],
                },
              },
            ],
            saved_intelligence_ids: [],
            pinned_topics: [],
            weekly_v1: [],
            needs_attention: [],
            operations: { source_count: 1 },
          }),
        };
      }
      if (url.includes("/videos?limit=24")) {
        return {
          ok: true,
          json: async () => ({
            videos: [
              {
                video_id: "vid-top",
                channel_id: "ch-1",
                channel_name: "Atlas Agent Lab",
                title: "State Machines Talk",
                provider: "YOUTUBE",
                duration_seconds: 1800,
                published_at: "2026-11-26T08:00:00Z",
                processing_status: "COMPLETE",
                last_updated: "2026-11-26T08:00:00Z",
                ai_brief: {
                  video_id: "vid-top",
                  headline_zh: "生产级状态机高优必看指南",
                  score: 9.4,
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  is_read: markedRead,
                },
              },
              {
                video_id: "vid-short",
                channel_id: "ch-1",
                channel_name: "Atlas Agent Lab",
                title: "42s Teaser #shorts",
                provider: "YOUTUBE",
                duration_seconds: 42,
                published_at: "2026-11-26T09:00:00Z",
                processing_status: "COMPLETE",
                last_updated: "2026-11-26T09:00:00Z",
                ai_brief: {
                  video_id: "vid-short",
                  headline_zh: "预热短片噪音",
                  score: 2.0,
                  recommendation_tier: "SKIP_NOISE",
                  content_bucket: "SHORTS_PROMO",
                  is_short_noise: true,
                  is_read: false,
                },
              },
            ],
          }),
        };
      }
      if (url.endsWith("/knowledge-delta")) {
        return {
          ok: true,
          json: async () => ({
            knowledge_delta: {
              window_start: "2026-11-19T00:00:00Z",
              window_end: "2026-11-26T00:00:00Z",
              timezone: "Asia/Shanghai",
              status: "available",
              detail_limit: 2,
              categories: [],
            },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);

  expect(await screen.findByText("高优待读队列")).toBeTruthy();
  expect(screen.getByText("生产级状态机高优必看指南")).toBeTruthy();
  expect(screen.queryByText("预热短片噪音")).toBeNull();
  expect(screen.getByRole("button", { name: "开始连续速读 (1)" })).toBeTruthy();

  // Compact validation disclosure keeps posture truth in DOM without noisy wall.
  expect(screen.getByText(/验证状态说明/)).toBeTruthy();
  expect(screen.getByText("这是验证状态，不是数值置信度。")).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "标已读：生产级状态机高优必看指南" }));
  await waitFor(() => expect(postedUrls.length).toBe(1));
  expect(await screen.findByText("本周高优内容已全部读完")).toBeTruthy();
});
