import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BilibiliImport } from "./BilibiliImport";
import {
  CreatorFollowingCapabilityState,
  CreatorFollowingDetail,
  FollowCreatorFromContent,
} from "./CreatorFollowing";
import { UiLanguageProvider } from "./uiLanguage";

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

const available: CreatorFollowingCapabilityState = {
  known: true, capability: { available: true, code: "CREATOR_FOLLOWING_AVAILABLE" },
};
const withdrawn: CreatorFollowingCapabilityState = {
  known: true,
  capability: {
    available: false,
    code: "CREATOR_TRACKING_UNAVAILABLE",
    message: "Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos.",
  },
};

const settings = (creator: CreatorFollowingCapabilityState) => (url: string) => {
  if (url.endsWith("/settings")) {
    return { ok: true, json: async () => ({ bilibili: { creator_following: creator.known ? creator.capability : null } }) };
  }
  return null;
};

test("creator Following is distinct from one-video import and sends canonical input", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    requests.push(url);
    const settingsReply = settings(available)(url);
    if (settingsReply) return settingsReply;
    expect(JSON.parse(String(options?.body))).toEqual({ input: "https://space.bilibili.com/123" });
    return { ok: true, json: async () => ({ source: { source_id: "bilibili-creator-123" } }) };
  }));
  localStorage.setItem("yia.ui-language", "en");
  render(<UiLanguageProvider><BilibiliImport onClose={() => {}} onSaved={() => {}} onProvider={() => {}} /></UiLanguageProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Follow a creator" }));
  const input = await screen.findByLabelText("Creator profile URL or numeric id");
  fireEvent.change(input, { target: { value: "https://space.bilibili.com/123" } });
  fireEvent.click(screen.getByRole("button", { name: "Follow creator" }));
  await screen.findByText("Creator followed. Check the Following detail for its starting point and source health.");
  expect(requests).toContain("/api/v1/sources/creators");
});

test("withdrawn creator Following removes the entry point and keeps video import", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => settings(withdrawn)(url) ?? { ok: true, json: async () => ({}) }));
  localStorage.setItem("yia.ui-language", "en");
  render(<UiLanguageProvider><BilibiliImport onClose={() => {}} onSaved={() => {}} onProvider={() => {}} /></UiLanguageProvider>);
  expect(await screen.findByText("Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos.")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Follow a creator" })).toBeNull();
  expect(screen.getByRole("button", { name: "Import public video" })).toBeTruthy();
});

test("a creator refusal is reported as risk control, not as a missing creator", async () => {
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("fetch", vi.fn(async (url: string) => settings(available)(url) ?? { ok: true, json: async () => ({
    source: {
      source_id: "bilibili-creator-123", display_name: "公开 UP 主", enabled: true,
      canonical_url: "https://space.bilibili.com/123", last_checked_at: null, last_success_at: null,
      tracking: { health: "RISK_CONTROLLED", coverage: "COMPLETE", update_count: 0, pending_count: 0 },
    }, recent_videos: [], source_runs: [],
  }) }));
  render(<UiLanguageProvider><CreatorFollowingDetail id="bilibili-creator-123" capability={available} onClose={() => {}} onRefresh={() => {}} /></UiLanguageProvider>);
  await screen.findByText("公开 UP 主");
  expect(screen.getByText("Bilibili has temporarily restricted public requests. Your stored Content is preserved.")).toBeTruthy();
  expect(screen.queryByText("This creator is not publicly accessible. No login is used.")).toBeNull();
});

test("follow versus baseline is reported honestly instead of claiming success", async () => {
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("fetch", vi.fn(async (url: string) => settings(available)(url) ?? { ok: true, json: async () => ({
    source: {
      source_id: "bilibili-creator-123", display_name: "公开 UP 主", enabled: false,
      canonical_url: "https://space.bilibili.com/123", last_checked_at: null, last_success_at: null,
      tracking: { health: "RISK_CONTROLLED", coverage: "BASELINE_PENDING", update_count: 0, pending_count: 0 },
    }, recent_videos: [], source_runs: [],
  }) }));
  render(<UiLanguageProvider><CreatorFollowingDetail id="bilibili-creator-123" capability={available} onClose={() => {}} onRefresh={() => {}} /></UiLanguageProvider>);
  await screen.findByText("公开 UP 主");
  expect(screen.getByText("No, no successful check has completed yet")).toBeTruthy();
  expect(screen.queryByText("Yes")).toBeNull();
});

test("Chinese creator Following explains baseline, pause and zero updates", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  vi.stubGlobal("fetch", vi.fn(async (url: string) => settings(available)(url) ?? { ok: true, json: async () => ({
    source: {
      source_id: "bilibili-creator-123", display_name: "公开 UP 主", enabled: false, canonical_url: "https://space.bilibili.com/123",
      last_checked_at: null, last_success_at: null, tracking: { health: "BASELINE_PENDING", coverage: "BASELINE_PENDING", update_count: 0, pending_count: 0 },
    }, recent_videos: [], source_runs: [],
  }) }));
  render(<UiLanguageProvider><CreatorFollowingDetail id="bilibili-creator-123" capability={available} onClose={() => {}} onRefresh={() => {}} /></UiLanguageProvider>);
  await screen.findByText("公开 UP 主");
  expect(screen.getByText("等待建立跟踪起点")).toBeTruthy();
  expect(screen.getByRole("button", { name: "继续关注" })).toBeTruthy();
  expect((screen.getByRole("button", { name: "立即检查" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("尚未发现新的公开视频。")).toBeTruthy();
});

test("withdrawn capability keeps a stored creator readable and disables Check Now", async () => {
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("fetch", vi.fn(async (url: string) => settings(withdrawn)(url) ?? { ok: true, json: async () => ({
    source: {
      source_id: "bilibili-creator-123", display_name: "公开 UP 主", enabled: true,
      canonical_url: "https://space.bilibili.com/123",
      last_checked_at: "2026-10-04T12:00:00Z", last_success_at: "2026-10-04T12:00:00Z",
      tracking: { health: "HEALTHY", coverage: "COMPLETE", baseline_at: "2026-10-04T12:00:00Z", update_count: 3, pending_count: 0 },
    }, recent_videos: [{ video_id: "bilibili-BV1xx411c7mD", title: "Stored video", processing_status: "IMPORTED" }], source_runs: [],
  }) }));
  render(<UiLanguageProvider><CreatorFollowingDetail id="bilibili-creator-123" capability={withdrawn} onClose={() => {}} onRefresh={() => {}} /></UiLanguageProvider>);
  await screen.findByText("公开 UP 主");
  expect(screen.getByText("Continuous creator tracking is currently unavailable")).toBeTruthy();
  expect(screen.getByText("Source checks are working")).toBeTruthy();
  expect(screen.getByText("Stored video")).toBeTruthy();
  expect((screen.getByRole("button", { name: "Check Now" }) as HTMLButtonElement).disabled).toBe(true);
});

test("follow from Content sends only Content identity", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn(async (url: string) => settings(available)(url) ?? { ok: true, json: async () => ({ source: {} }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><FollowCreatorFromContent id="bilibili-BV1xx411c7mD" capability={available} /></UiLanguageProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Follow this creator" }));
  await waitFor(() => expect(fetch.mock.calls.some(call => String(call[0]).endsWith("/follow-creator"))).toBe(true));
  expect(fetch.mock.calls.find(call => String(call[0]).endsWith("/follow-creator"))?.[0]).toBe("/api/v1/videos/bilibili-BV1xx411c7mD/follow-creator");
});

test("follow from Content is disabled and silent while the capability is withdrawn", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn(async (url: string) => settings(withdrawn)(url) ?? { ok: true, json: async () => ({}) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><FollowCreatorFromContent id="bilibili-BV1xx411c7mD" capability={withdrawn} /></UiLanguageProvider>);
  expect((await screen.findByRole("button", { name: "Continuous creator tracking is currently unavailable" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetch.mock.calls.some(call => String(call[0]).includes("follow-creator"))).toBe(false);
});