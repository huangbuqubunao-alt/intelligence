import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BilibiliImport } from "./BilibiliImport";
import { CreatorFollowingDetail, FollowCreatorFromContent } from "./CreatorFollowing";
import { UiLanguageProvider } from "./uiLanguage";

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

test("creator Following is distinct from one-video import and sends canonical input", async () => {
  const requests: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    requests.push(url); expect(JSON.parse(String(options?.body))).toEqual({ input: "https://space.bilibili.com/123" });
    return { ok: true, json: async () => ({ source: { source_id: "bilibili-creator-123" } }) };
  }));
  localStorage.setItem("yia.ui-language", "en");
  render(<UiLanguageProvider><BilibiliImport onClose={() => {}} onSaved={() => {}} onProvider={() => {}} /></UiLanguageProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Follow a creator" }));
  fireEvent.change(screen.getByLabelText("Creator profile URL or numeric id"), { target: { value: "https://space.bilibili.com/123" } });
  fireEvent.click(screen.getByRole("button", { name: "Follow creator" }));
  await screen.findByText("Creator followed. Check the Following detail for its starting point and source health.");
  expect(requests).toEqual(["/api/v1/sources/creators"]);
});

test("Chinese creator Following explains baseline, pause and zero updates", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ source: {
    source_id: "bilibili-creator-123", display_name: "公开 UP 主", enabled: false, canonical_url: "https://space.bilibili.com/123",
    last_checked_at: null, last_success_at: null, tracking: { health: "BASELINE_PENDING", coverage: "BASELINE_PENDING", update_count: 0, pending_count: 0 },
  }, recent_videos: [], source_runs: [] }) })));
  render(<UiLanguageProvider><CreatorFollowingDetail id="bilibili-creator-123" onClose={() => {}} onRefresh={() => {}} /></UiLanguageProvider>);
  await screen.findByText("公开 UP 主");
  expect(screen.getByText("等待建立跟踪起点")).toBeTruthy();
  expect(screen.getByRole("button", { name: "继续关注" })).toBeTruthy();
  expect((screen.getByRole("button", { name: "立即检查" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("尚未发现新的公开视频。" )).toBeTruthy();
});

test("follow from Content sends only Content identity", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn(async (_url: string, _options?: RequestInit) => ({ ok: true, json: async () => ({ source: {} }) }));
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><FollowCreatorFromContent id="bilibili-BV1xx411c7mD" /></UiLanguageProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Follow this creator" }));
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
  expect(fetch.mock.calls[0]?.[0]).toBe("/api/v1/videos/bilibili-BV1xx411c7mD/follow-creator");
});

test.each([['en', 'Follow channel', 'Channel URL, @handle or channel id'], ['zh-CN', '关注频道', '频道链接、@用户名或频道 ID']])('shared YouTube form in %s', async (language, action, label) => {
  const { CreatorFollowForm } = await import('./CreatorFollowing');
  localStorage.setItem('yia.ui-language', language);
  const requests: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => { requests.push(url); return { ok: true, json: async () => ({ source: {} }) }; }));
  render(<UiLanguageProvider><CreatorFollowForm provider="YOUTUBE" onSaved={() => {}} /></UiLanguageProvider>);
  fireEvent.change(screen.getByLabelText(label), { target: { value: 'https://youtube.com/@public' } });
  fireEvent.click(screen.getByRole('button', { name: action }));
  await waitFor(() => expect(requests).toEqual(['/api/v1/sources/channels']));
});

test('YouTube Content follow sends only trusted Content identity', async () => {
  localStorage.setItem('yia.ui-language', 'en');
  const fetch = vi.fn(async (_url: string, _options?: RequestInit) => ({ ok: true, json: async () => ({ source: {} }) }));
  vi.stubGlobal('fetch', fetch);
  render(<UiLanguageProvider><FollowCreatorFromContent provider="YOUTUBE" id="aaaaaaaaaaa" /></UiLanguageProvider>);
  fireEvent.click(screen.getByRole('button', { name: 'Follow this channel' }));
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
  expect(fetch.mock.calls[0]?.[0]).toBe('/api/v1/videos/aaaaaaaaaaa/follow-channel');
  expect(JSON.parse(String(fetch.mock.calls[0]?.[1]?.body))).toEqual({});
});
