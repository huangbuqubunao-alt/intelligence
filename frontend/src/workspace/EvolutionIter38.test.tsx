import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { buildFollowingAuditMarkdown } from "./followingAuditExport";

const origCreateObjectURL = URL.createObjectURL;
const origRevokeObjectURL = URL.revokeObjectURL;

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Iteration 38 (EVO-W7-03): #Following instant search & channel signal audit export", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.onboarding_completed.v1", "1");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Following";
  });

  afterEach(() => {
    cleanup();
    URL.createObjectURL = origCreateObjectURL;
    URL.revokeObjectURL = origRevokeObjectURL;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  it("buildFollowingAuditMarkdown ranks top-signal channels and surfaces low-signal/health warnings", () => {
    const res = buildFollowingAuditMarkdown(
      [
        {
          source_id: "src-high",
          display_name: "Atlas Agent Lab",
          provider: "YOUTUBE",
          canonical_url: "https://youtube.com/@atlas",
          enabled: true,
        },
        {
          source_id: "src-noisy",
          display_name: "Hype Clips Daily",
          provider: "YOUTUBE",
          canonical_url: "https://youtube.com/@hype",
          enabled: true,
          last_error: { code: "RATE_LIMITED" },
        },
      ],
      {
        "src-high": {
          source_id: "src-high",
          channel_key: "atlas",
          channel_label: "Atlas Agent Lab",
          total_videos: 10,
          distilled_count: 10,
          long_form_count: 9,
          shorts_count: 1,
          must_watch_count: 6,
          worth_skimming_count: 3,
          unread_long_count: 2,
          avg_long_score: 9.1,
          signal_rate_pct: 90,
        },
        "src-noisy": {
          source_id: "src-noisy",
          channel_key: "hype",
          channel_label: "Hype Clips Daily",
          total_videos: 10,
          distilled_count: 10,
          long_form_count: 3,
          shorts_count: 7,
          must_watch_count: 0,
          worth_skimming_count: 3,
          unread_long_count: 1,
          avg_long_score: 5.4,
          signal_rate_pct: 30,
        },
      },
      true,
    );

    expect(res.sourceCount).toBe(2);
    expect(res.filename).toMatch(/^following-signal-audit-\d{4}-\d{2}-\d{2}\.md$/);
    expect(res.markdown).toContain("# 关注信源信息食谱体检报告");
    expect(res.markdown).toContain("整体干货信噪比：60%");
    expect(res.markdown).toContain("1. **Atlas Agent Lab** (YouTube)");
    expect(res.markdown).toContain("## 低干货 / Shorts 噪音待评估清单");
    expect(res.markdown).toContain("Hype Clips Daily");
    expect(res.markdown).toContain("## 状态异常与待处理提醒");
  });

  it("filters Following sources instantly, offers clear-search recovery, and exports signal audit .md", async () => {
    const blobs: Blob[] = [];
    URL.createObjectURL = vi.fn((blob: Blob | MediaSource) => {
      blobs.push(blob as Blob);
      return "blob:audit-md";
    });
    URL.revokeObjectURL = vi.fn();

    vi.stubGlobal("fetch", (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/system")) {
        return okJson({ health: "ready", edition: "LOCAL" });
      }
      if (url.includes("/api/v1/settings")) {
        return okJson({
          bilibili: { creator_following: { available: false, code: "CREATOR_TRACKING_UNAVAILABLE" } },
          youtube: { channel_following: { available: true, code: "AVAILABLE" } },
        });
      }
      if (url.includes("/api/v1/sources/check-stale")) {
        return okJson({ checks: [] });
      }
      if (url.includes("/api/v1/sources")) {
        return okJson({
          sources: [
            {
              source_id: "src1",
              source_type: "CHANNEL",
              provider: "YOUTUBE",
              display_name: "Builder Architecture Lab",
              canonical_url: "https://youtube.com/@builder",
              enabled: true,
              processing_policy: "FULL_INTELLIGENCE",
              last_error: null,
              tracking: { health: "HEALTHY", coverage: "LIVE", update_count: 1, pending_count: 0 },
            },
            {
              source_id: "src2",
              source_type: "LOCAL_LIBRARY",
              provider: "LOCAL",
              display_name: "Local Library",
              canonical_url: "local://library",
              enabled: true,
              processing_policy: "FULL_INTELLIGENCE",
              last_error: null,
              tracking: null,
            },
          ],
          ai_signal_by_source: {
            src1: {
              source_id: "src1",
              channel_key: "builder",
              channel_label: "Builder Architecture Lab",
              total_videos: 4,
              distilled_count: 4,
              long_form_count: 4,
              shorts_count: 0,
              must_watch_count: 3,
              worth_skimming_count: 1,
              unread_long_count: 1,
              avg_long_score: 9.0,
              signal_rate_pct: 100,
            },
          },
        });
      }
      return okJson({});
    });

    render(<App />);

    const searchInput = await screen.findByLabelText("搜索订阅信源");
    expect(screen.getByText("Builder Architecture Lab")).toBeTruthy();

    fireEvent.change(searchInput, { target: { value: "Builder" } });
    expect(screen.getByText("Builder Architecture Lab")).toBeTruthy();
    expect(screen.queryByText("Local library")).toBeNull();

    fireEvent.change(searchInput, { target: { value: "NonExistentChannelXYZ" } });
    expect(await screen.findByText(/未找到匹配「NonExistentChannelXYZ」的订阅信源/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "清空搜索" }));
    expect(screen.getByText("Builder Architecture Lab")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: /导出信源体检 \(\.md\)/ }));
    await waitFor(() => {
      expect(screen.getByText(/已导出信源体检 \(\.md · 2 个信源\)/)).toBeTruthy();
    });

    expect(blobs.length).toBeGreaterThanOrEqual(1);
    const mdText = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
      reader.readAsText(blobs[blobs.length - 1]);
    });
    expect(mdText).toContain("# 关注信源信息食谱体检报告");
    expect(mdText).toContain("Builder Architecture Lab");
  });
});
