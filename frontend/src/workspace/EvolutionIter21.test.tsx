import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import {
  clearReadingHistory,
  estimateReadingMinutes,
  readReadingHistory,
  recordReadingVisit,
} from "./readingHistory";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 21 — Reader study continuity, reading time & comfort typography", () => {
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

  it("estimates reading time cleanly from CJK/English text and duration fallback", () => {
    expect(estimateReadingMinutes({ text: "一".repeat(700) })).toBe(2);
    expect(estimateReadingMinutes({ text: "", durationSeconds: 600 })).toBe(10);
    expect(estimateReadingMinutes({ text: "", durationSeconds: 0 })).toBeNull();
  });

  it("records Reader visits to Home Continue Reading rail and toggles Reader comfort typography", async () => {
    location.hash = "#Content/vidStudy1";
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path.startsWith("/api/v1/dashboard")) {
          return jsonResponse({
            intelligence: [],
            saved_intelligence_ids: [],
            pinned_topics: [],
            weekly_v1: [],
            needs_attention: [],
            operations: { source_count: 1 },
            demo_mode: false,
          });
        }
        if (path === "/api/v1/videos/vidStudy1") {
          return jsonResponse({
            video: {
              video_id: "vidStudy1",
              title: "Deep Agent Evaluation Loop",
              channel_name: "Research Lab",
              provider: "YOUTUBE",
              media_kind: "VIDEO",
              processing_status: "PROCESSED",
              duration_seconds: 540,
            },
            transcript: {
              status: "AVAILABLE",
              text: "Agent evaluation requires repeatable harnesses and golden test suites. ".repeat(20),
              timed_segments: [],
            },
            note: { v2: { status: "AVAILABLE", summary: "Evaluation guide summary", core_points: [] } },
            intelligence_result: { status: "AVAILABLE", items: [] },
            evidence: [],
            history: [],
          });
        }
        if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
          return jsonResponse({
            videos: [
              {
                video_id: "vidStudy1",
                title: "Deep Agent Evaluation Loop",
                channel_name: "Research Lab",
                provider: "YOUTUBE",
                media_kind: "VIDEO",
                processing_status: "PROCESSED",
              },
            ],
          });
        }
        if (path === "/api/v1/workspace-ai/capabilities") {
          return jsonResponse({ ready: false, model_name: null, transcriber_ready: false });
        }
        if (path === "/api/v1/workspace-ai/research/sessions") {
          return jsonResponse({ sessions: [] });
        }
        return jsonResponse({});
      }),
    );

    render(<App />);
    expect(await screen.findByText(/Deep Agent Evaluation Loop/i)).toBeTruthy();

    const readTimePill = await screen.findByText(/约 \d+ 分钟精读/);
    expect(readTimePill).toBeTruthy();

    const comfortBtn = screen.getByRole("button", { name: "开启舒朗阅读排版" });
    await user.click(comfortBtn);
    const activeComfortBtn = screen.getByRole("button", { name: "切回标准阅读排版" });
    expect(activeComfortBtn.getAttribute("aria-pressed")).toBe("true");
    expect(document.querySelector(".detail-panel.is-reading-comfort")).not.toBeNull();

    await waitFor(() => {
      const history = readReadingHistory();
      expect(history.some((entry) => entry.videoId === "vidStudy1")).toBe(true);
    });

    await user.click(screen.getByRole("button", { name: /首页|Home/ }));

    expect(await screen.findByText("最近阅读 · 继续精读")).toBeTruthy();
    expect(screen.getByText("Deep Agent Evaluation Loop")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "清空" }));
    await waitFor(() => {
      expect(screen.queryByText("最近阅读 · 继续精读")).toBeNull();
    });
    expect(readReadingHistory()).toEqual([]);

    recordReadingVisit({ videoId: "x", title: "Temp" });
    clearReadingHistory();
  });
});
