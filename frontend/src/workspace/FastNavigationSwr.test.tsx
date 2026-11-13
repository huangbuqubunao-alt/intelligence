import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

const jsonResponse = (body: object) => ({
  ok: true,
  status: 200,
  json: async () => body,
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

it("renders cached Content and Intelligence immediately on tab return without flashing loading skeletons while revalidating", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content";

  let videosReadCount = 0;
  let resolveSecondVideosRead: ((value: ReturnType<typeof jsonResponse>) => void) | null = null;
  let intelReadCount = 0;
  let resolveSecondIntelRead: ((value: ReturnType<typeof jsonResponse>) => void) | null = null;

  const fetchMock = vi.fn((path: string) => {
    if (path.endsWith("/videos")) {
      videosReadCount += 1;
      if (videosReadCount === 1) {
        return Promise.resolve(
          jsonResponse({
            videos: [
              {
                video_id: "vid-alpha",
                provider: "YOUTUBE",
                title: "极速内容 Alpha",
                channel_name: "OpenAI",
                processing_status: "ORGANIZED",
                tracked_content_retry: { request: null, retry_allowed: false, expected_job_id: null },
              },
            ],
          }),
        );
      }
      return new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
        resolveSecondVideosRead = resolve;
      });
    }
    if (path.endsWith("/intelligence")) {
      intelReadCount += 1;
      if (intelReadCount === 1) {
        return Promise.resolve(
          jsonResponse({
            intelligence: [],
            activity: [
              {
                video_id: "vid-alpha",
                title: "极速洞察活动 Alpha",
                status: "WAITING_CONTENT",
              },
            ],
          }),
        );
      }
      return new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
        resolveSecondIntelRead = resolve;
      });
    }
    if (path.endsWith("/saved-intelligence")) {
      return Promise.resolve(jsonResponse({ saved: [] }));
    }
    return Promise.resolve(jsonResponse({}));
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);
  expect(await screen.findByText("极速内容 Alpha")).toBeTruthy();

  // Navigate to Intelligence (#Intelligence)
  fireEvent.click(screen.getByRole("button", { name: "洞察" }));
  expect(await screen.findByText("极速洞察活动 Alpha")).toBeTruthy();

  // Navigate back to Content (#Content) while second /videos fetch stays pending:
  // Cached item MUST be visible immediately on frame 0 without "正在加载内容…" flash!
  fireEvent.click(screen.getByRole("button", { name: "内容" }));
  expect(screen.queryByText("正在加载内容…")).toBeNull();
  expect(screen.getByText("极速内容 Alpha")).toBeTruthy();

  // When background SWR revalidation resolves with updated list, UI updates seamlessly
  expect(resolveSecondVideosRead).not.toBeNull();
  await act(async () => {
    resolveSecondVideosRead!(
      jsonResponse({
        videos: [
          {
            video_id: "vid-alpha",
            provider: "YOUTUBE",
            title: "极速内容 Alpha",
            channel_name: "OpenAI",
            processing_status: "ORGANIZED",
            tracked_content_retry: { request: null, retry_allowed: false, expected_job_id: null },
          },
          {
            video_id: "vid-beta",
            provider: "YOUTUBE",
            title: "极速内容 Beta",
            channel_name: "Greg Isenberg",
            processing_status: "ORGANIZED",
            tracked_content_retry: { request: null, retry_allowed: false, expected_job_id: null },
          },
        ],
      }),
    );
  });
  expect(await screen.findByText("极速内容 Beta")).toBeTruthy();

  // Navigate back to Intelligence (#Intelligence) while second /intelligence fetch stays pending:
  // Cached activity MUST be visible immediately without "正在加载已验证的洞察…" flash!
  fireEvent.click(screen.getByRole("button", { name: "洞察" }));
  expect(screen.queryByText("正在加载已验证的洞察…")).toBeNull();
  expect(screen.queryByText("正在加载已验证洞察…")).toBeNull();
  expect(screen.getByText("极速洞察活动 Alpha")).toBeTruthy();
  expect(resolveSecondIntelRead).not.toBeNull();
});

it("retains existing Content list during 2-second background status polling instead of flashing loading state", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content";

  let pollCount = 0;
  let resolvePoll: ((value: ReturnType<typeof jsonResponse>) => void) | null = null;
  vi.stubGlobal(
    "fetch",
    vi.fn((path: string) => {
      if (path.endsWith("/videos")) {
        pollCount += 1;
        if (pollCount === 1) {
          return Promise.resolve(
            jsonResponse({
              videos: [
                {
                  video_id: "vid-polling",
                  provider: "YOUTUBE",
                  title: "正在读取字幕的视频",
                  processing_status: "READING_CAPTIONS",
                  tracked_content_retry: { request: null, retry_allowed: false, expected_job_id: null },
                },
              ],
            }),
          );
        }
        return new Promise<ReturnType<typeof jsonResponse>>((resolve) => {
          resolvePoll = resolve;
        });
      }
      return Promise.resolve(jsonResponse({}));
    }),
  );

  render(<App />);
  expect(await screen.findByText("正在读取字幕的视频")).toBeTruthy();

  // Advance past the 2000ms auto-poll timer while the poll response is still pending
  await act(async () => {
    vi.advanceTimersByTime(2100);
  });
  expect(pollCount).toBeGreaterThanOrEqual(2);
  expect(screen.queryByText("正在加载内容…")).toBeNull();
  expect(screen.getByText("正在读取字幕的视频")).toBeTruthy();

  await act(async () => {
    resolvePoll?.(
      jsonResponse({
        videos: [
          {
            video_id: "vid-polling",
            provider: "YOUTUBE",
            title: "正在读取字幕的视频",
            processing_status: "ORGANIZED",
            tracked_content_retry: { request: null, retry_allowed: false, expected_job_id: null },
          },
        ],
      }),
    );
  });
  expect(screen.getByText("正在读取字幕的视频")).toBeTruthy();
});
