import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

test("Content organizes 2-tier triage toolbar, tracks secondary filter count on toggle, and preserves search/sort/keyboard", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url === "/api/v1/videos" || url.startsWith("/api/v1/videos?")) {
        return {
          ok: true,
          json: async () => ({
            videos: [
              {
                video_id: "vid-yt",
                provider: "YOUTUBE",
                channel_id: "UC1",
                channel_name: "Atlas Lab",
                title: "Production State Machines",
                published_at: "2026-11-26T08:00:00Z",
                processing_status: "READY",
                last_updated: "2026-11-26T08:00:00Z",
                duration_seconds: 1200,
                ai_brief: {
                  video_id: "vid-yt",
                  headline_zh: "确定性状态机架构指南",
                  summary_zh: "状态机设计。",
                  score: 9.4,
                  score_reason_zh: "高分指南",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["Agent"],
                  topic_cluster_zh: "AI Agent 工程架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
              {
                video_id: "vid-local",
                provider: "LOCAL",
                media_kind: "TEXT",
                channel_id: "local",
                channel_name: "Local",
                title: "local-architecture.md",
                imported_at: "2026-11-27T00:00:00Z",
                processing_status: "READY",
                last_updated: "2026-11-27T00:00:00Z",
                ai_brief: {
                  video_id: "vid-local",
                  headline_zh: "本地优先架构笔记",
                  summary_zh: "本地笔记。",
                  score: 8.6,
                  score_reason_zh: "笔记拆解",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "TUTORIAL",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["Local-First"],
                  topic_cluster_zh: "一人公司与 AI 产品化",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
            ],
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  const toggleBtn = await screen.findByRole("button", { name: "筛选" });
  expect(toggleBtn.getAttribute("aria-expanded")).toBe("false");

  expect(document.querySelector(".library-filter-primary")).toBeTruthy();
  const secondaryEl = document.querySelector(".library-filter-secondary");
  expect(secondaryEl).toBeTruthy();
  expect(secondaryEl?.classList.contains("is-mobile-open")).toBe(false);

  fireEvent.click(toggleBtn);
  expect(toggleBtn.getAttribute("aria-expanded")).toBe("true");
  expect(secondaryEl?.classList.contains("is-mobile-open")).toBe(true);

  const topicSelect = screen.getByRole("combobox", { name: "按专题筛选内容" });
  fireEvent.change(topicSelect, { target: { value: "AI Agent 工程架构" } });

  await waitFor(() => {
    expect(toggleBtn.textContent).toContain("筛选 (1)");
  });
  expect(screen.getByText("Production State Machines")).toBeTruthy();
  expect(screen.queryByText("local-architecture.md")).toBeNull();

  const sortTop = screen.getByRole("button", { name: "高分优先" });
  fireEvent.click(sortTop);
  await waitFor(() => {
    expect(toggleBtn.textContent).toContain("筛选 (2)");
  });

  fireEvent.click(screen.getByRole("button", { name: "重置筛选" }));
  await waitFor(() => {
    expect(screen.getByText("local-architecture.md")).toBeTruthy();
    expect(toggleBtn.textContent).toContain("筛选 (1)");
  });
});
