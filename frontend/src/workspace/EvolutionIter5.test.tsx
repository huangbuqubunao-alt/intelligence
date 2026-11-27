import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
  location.hash = "#Following";
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

test("Following displays Channel Signal-to-Noise digest and toggles low-signal/Shorts review filter", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.endsWith("/capabilities/creator-following")) {
        return { ok: true, json: async () => ({ available: false }) };
      }
      if (url.endsWith("/sources/check-stale")) {
        return { ok: true, json: async () => ({ checks: [] }) };
      }
      if (url.endsWith("/sources")) {
        return {
          ok: true,
          json: async () => ({
            sources: [
              {
                source_id: "src-high",
                source_type: "CHANNEL",
                provider: "YOUTUBE",
                canonical_url: "https://www.youtube.com/@atlas",
                channel_id: "UCatlas001",
                display_name: "Atlas Agent Lab (Demo)",
                enabled: true,
                processing_policy: "DISCOVER_ONLY",
                processing_mode: "ORGANIZE_CONTENT",
                last_checked_at: "2026-11-26T08:00:00Z",
                last_success_at: "2026-11-26T08:00:00Z",
                last_error: null,
                insight_count: 2,
              },
              {
                source_id: "src-noisy",
                source_type: "CHANNEL",
                provider: "YOUTUBE",
                canonical_url: "https://www.youtube.com/@foundry",
                channel_id: "UCfoundry002",
                display_name: "Local-First Foundry (Demo)",
                enabled: true,
                processing_policy: "DISCOVER_ONLY",
                processing_mode: "ORGANIZE_CONTENT",
                last_checked_at: "2026-11-26T08:00:00Z",
                last_success_at: "2026-11-26T08:00:00Z",
                last_error: null,
                insight_count: 1,
              },
            ],
            ai_signal_by_source: {
              "src-high": {
                source_id: "src-high",
                channel_key: "Atlas Agent Lab (Demo)",
                channel_label: "Atlas Agent Lab (Demo)",
                total_videos: 2,
                distilled_count: 2,
                long_form_count: 2,
                shorts_count: 0,
                must_watch_count: 2,
                worth_skimming_count: 0,
                unread_long_count: 1,
                avg_long_score: 9.1,
                signal_rate_pct: 100,
              },
              "src-noisy": {
                source_id: "src-noisy",
                channel_key: "Local-First Foundry (Demo)",
                channel_label: "Local-First Foundry (Demo)",
                total_videos: 2,
                distilled_count: 2,
                long_form_count: 1,
                shorts_count: 1,
                must_watch_count: 1,
                worth_skimming_count: 0,
                unread_long_count: 1,
                avg_long_score: 8.8,
                signal_rate_pct: 50,
              },
            },
          }),
        };
      }
      return { ok: true, json: async () => ({}) };
    }),
  );

  render(<App />);
  const digest = await screen.findByRole("region", { name: "频道信噪比健康简报" });
  expect(digest.textContent).toContain("整体干货信噪比 75%");
  expect(digest.textContent).toContain("最高信噪比：Atlas Agent Lab (Demo) · 均分 9.1");

  const reviewBtn = screen.getByRole("button", { name: /待评估信源 \(1\)/ });
  fireEvent.click(reviewBtn);

  await waitFor(() => {
    expect(screen.queryByText("Atlas Agent Lab (Demo)")).toBeNull();
  });
  expect(screen.getByText("Local-First Foundry (Demo)")).toBeTruthy();

  fireEvent.click(reviewBtn);
  await waitFor(() => {
    expect(screen.getByText("Atlas Agent Lab (Demo)")).toBeTruthy();
  });
});
