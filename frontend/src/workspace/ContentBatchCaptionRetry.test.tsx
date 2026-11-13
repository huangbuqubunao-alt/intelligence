import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

it.each(["en", "zh-CN"])(
  "recovers retryable YouTube captions sequentially from #Content in %s",
  async (language) => {
    localStorage.setItem("yia.ui-language", language);
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Content";

    const stateByVideo: Record<string, "IDLE" | "ACQUIRING" | "SUCCEEDED"> = {
      "vid-alpha": "IDLE",
      "vid-beta": "IDLE",
    };
    const postOrder: string[] = [];

    const makeReceipt = (videoId: string, state: string, expectedJobId: string) => ({
      request_id: `tracked-content-retry:v1:${videoId}`,
      video_id: videoId,
      source_id: "youtube-channel-UCXZCJLdBC09xxGZ6gcdrc6A",
      expected_job_id: expectedJobId,
      target_job_id: `tracked-content-retry-job:v1:${videoId}`,
      state,
      revision: state === "SUCCEEDED" ? 5 : 2,
      error_code: null,
      can_resume_local: false,
      can_close_local: false,
      can_cancel: false,
    });

    const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      if (path.endsWith("/videos") && method === "GET") {
        return {
          ok: true,
          json: async () => ({
            videos: [
              {
                video_id: "vid-alpha",
                provider: "YOUTUBE",
                channel_id: "UCXZCJLdBC09xxGZ6gcdrc6A",
                channel_name: "OpenAI",
                title: "Alpha Frontier Video",
                source_url: "https://www.youtube.com/watch?v=vid-alpha01",
                published_at: "2026-10-20T13:00:00Z",
                processing_status: stateByVideo["vid-alpha"] === "SUCCEEDED" ? "ORGANIZED" : "FAILED",
                tracked_content_retry:
                  stateByVideo["vid-alpha"] === "IDLE"
                    ? { request: null, retry_allowed: true, expected_job_id: "job-alpha" }
                    : {
                        request: makeReceipt("vid-alpha", stateByVideo["vid-alpha"], "job-alpha"),
                        retry_allowed: false,
                        expected_job_id: null,
                      },
              },
              {
                video_id: "vid-beta",
                provider: "YOUTUBE",
                channel_id: "UCXZCJLdBC09xxGZ6gcdrc6A",
                channel_name: "OpenAI",
                title: "Beta Systems Video",
                source_url: "https://www.youtube.com/watch?v=vid-beta001",
                published_at: "2026-10-19T13:00:00Z",
                processing_status: stateByVideo["vid-beta"] === "SUCCEEDED" ? "ORGANIZED" : "FAILED",
                tracked_content_retry:
                  stateByVideo["vid-beta"] === "IDLE"
                    ? { request: null, retry_allowed: true, expected_job_id: "job-beta" }
                    : {
                        request: makeReceipt("vid-beta", stateByVideo["vid-beta"], "job-beta"),
                        retry_allowed: false,
                        expected_job_id: null,
                      },
              },
            ],
          }),
        };
      }
      for (const [vid, jobId] of [
        ["vid-alpha", "job-alpha"],
        ["vid-beta", "job-beta"],
      ] as const) {
        if (path.endsWith(`/content/${vid}/retry`) && method === "POST") {
          postOrder.push(vid);
          stateByVideo[vid] = "ACQUIRING";
          return {
            ok: true,
            json: async () => ({
              tracked_content_retry: makeReceipt(vid, "QUEUED", jobId),
            }),
          };
        }
        if (path.endsWith(`/content/${vid}/retry`) && method === "GET") {
          if (stateByVideo[vid] === "ACQUIRING") {
            stateByVideo[vid] = "SUCCEEDED";
          }
          return {
            ok: true,
            json: async () => ({
              tracked_content_retry:
                stateByVideo[vid] === "IDLE"
                  ? { request: null, retry_allowed: true, expected_job_id: jobId }
                  : {
                      request: makeReceipt(vid, stateByVideo[vid], jobId),
                      retry_allowed: false,
                      expected_job_id: null,
                    },
            }),
          };
        }
      }
      return { ok: true, json: async () => ({}) };
    });

    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const buttonLabel =
      language === "en" ? /Retry all failed captions/i : /一键恢复失败字幕/;
    const recoverBtn = await screen.findByRole("button", { name: buttonLabel });
    fireEvent.click(recoverBtn);

    await waitFor(
      () => {
        expect(postOrder).toEqual(["vid-alpha", "vid-beta"]);
        expect(stateByVideo["vid-alpha"]).toBe("SUCCEEDED");
        expect(stateByVideo["vid-beta"]).toBe("SUCCEEDED");
      },
      { timeout: 6000 },
    );
  },
);
