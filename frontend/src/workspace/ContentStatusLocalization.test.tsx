import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

/**
 * A stored Content whose source no longer verifies must be reported in the
 * user's own language.  The resolved label is passed to the status component
 * as already-resolved text; before that, the enum de-CamelCasing fallback ran
 * the sentence through lowercasing and the Chinese interface showed English.
 */

const response = (value: object) =>
  Promise.resolve({ ok: true, json: async () => value });

const BILIBILI_UNTRUSTED = "The stored Bilibili source failed verification. Its Evidence is unavailable.";
const BILIBILI_UNTRUSTED_ZH = "已保存的哔哩哔哩来源未通过验证，其证据不可用。";
const LOCAL_UNTRUSTED = "The imported snapshot failed verification. Existing Evidence is unavailable.";
const LOCAL_UNTRUSTED_ZH = "已导入的快照未通过验证，现有证据暂不可用。";

const untrustedVideo = (provider: string, processing_status: string) => ({
  video_id: provider === "LOCAL" ? "local-untrusted" : "bilibili-untrusted",
  channel_name: "Fixture channel",
  title: "Stored source that no longer verifies",
  source_url: "https://example.invalid/source",
  published_at: "2026-09-01T00:00:00Z",
  imported_at: "2026-09-01T00:00:00Z",
  provider,
  media_kind: provider === "LOCAL" ? "TEXT" : "VIDEO",
  processing_status,
  deep_analysis: { status: "NOT_REQUESTED", reason: null },
});

type FixtureVideo = ReturnType<typeof untrustedVideo>;

const captionlessVideo: FixtureVideo = {
  ...untrustedVideo("BILIBILI", "CAPTION_UNAVAILABLE"),
  video_id: "bilibili-captionless",
};

const detail = (video: FixtureVideo) => ({
  video,
  transcript: { status: "UNAVAILABLE", code: `${video.provider}_SOURCE_UNTRUSTED` },
  note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
  intelligence_result: { status: "NOT_PROCESSED" },
  history: [],
});

const shown = () => document.body.textContent ?? "";

const stub = (videos: FixtureVideo[]) => vi.stubGlobal("fetch", vi.fn((input: string) => {
  const path = String(input);
  if (path.endsWith("/knowledge-delta")) return response({ knowledge_delta: { window_start: "2026-09-26T08:00:00.000000Z", window_end: "2026-10-03T08:00:00.000000Z", timezone: "Asia/Shanghai", status: "available", detail_limit: 2, categories: [] } });
  if (path.endsWith("/videos")) return response({ videos });
  const match = videos.find((video) => path.endsWith(`/videos/${video.video_id}`));
  if (match) return response(detail(match));
  return response({});
}));

afterEach(() => { vi.unstubAllGlobals(); });

const openContent = async (expected: string) => {
  fireEvent.click(screen.getByRole("button", { name: /Stored source that no longer verifies/ }));
  await waitFor(() => expect(screen.getAllByText(expected).length).toBeGreaterThan(0));
};

test("an untrusted Bilibili source is localized on the Content list and detail in both languages", async () => {
  for (const [language, expected] of [["zh-CN", BILIBILI_UNTRUSTED_ZH], ["en", BILIBILI_UNTRUSTED]] as const) {
    location.hash = "";
    localStorage.setItem("yia.ui-language", language);
    stub([untrustedVideo("BILIBILI", "SOURCE_UNTRUSTED")]);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: language === "zh-CN" ? "内容" : "Content" }));
    await waitFor(() => expect(screen.getAllByText(expected).length).toBeGreaterThan(0));
    // The sentence is rendered verbatim, never de-CamelCased into a variant.
    expect(shown()).not.toContain("The stored bilibili source failed verification. its evidence is unavailable.");
    expect(shown()).not.toContain("SOURCE_UNTRUSTED");
    await openContent(expected);
    expect(shown()).not.toContain("SOURCE_UNTRUSTED");
    expect(shown()).not.toContain("The stored bilibili source failed verification. its evidence is unavailable.");
    screen.getByRole("button", { name: language === "zh-CN" ? "返回内容" : "Back to Content" }).click();
    document.body.innerHTML = "";
  }
});

test("an untrusted Local source is localized on the Content list and detail in both languages", async () => {
  for (const [language, expected] of [["zh-CN", LOCAL_UNTRUSTED_ZH], ["en", LOCAL_UNTRUSTED]] as const) {
    location.hash = "";
    localStorage.setItem("yia.ui-language", language);
    stub([untrustedVideo("LOCAL", "LOCAL_SOURCE_UNTRUSTED")]);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: language === "zh-CN" ? "内容" : "Content" }));
    await waitFor(() => expect(screen.getAllByText(expected).length).toBeGreaterThan(0));
    expect(shown()).not.toContain("LOCAL_SOURCE_UNTRUSTED");
    await openContent(expected);
    expect(shown()).not.toContain("LOCAL_SOURCE_UNTRUSTED");
    expect(shown()).not.toContain("Local source untrusted");
    screen.getByRole("button", { name: language === "zh-CN" ? "返回内容" : "Back to Content" }).click();
    document.body.innerHTML = "";
  }
});

test("a Bilibili Content without a public caption stays an honest metadata-only record", async () => {
  for (const [language, unavailable, metadataOnly] of [
    ["zh-CN", "暂无可用的公开字幕", "摘要和证据需要可信字幕"],
    ["en", "Public captions are unavailable", "Summary and Evidence require trusted captions"],
  ] as const) {
    location.hash = "";
    localStorage.setItem("yia.ui-language", language);
    stub([captionlessVideo]);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: language === "zh-CN" ? "内容" : "Content" }));
    await waitFor(() => expect(screen.getAllByText(unavailable).length).toBeGreaterThan(0));
    fireEvent.click(screen.getByRole("button", { name: /Stored source that no longer verifies/ }));
    await waitFor(() => expect(shown()).toContain(metadataOnly));
    // No transcript is fabricated, and there is no speech-to-text fallback.
    expect(document.querySelectorAll(".timed-transcript").length).toBe(0);
    expect(shown()).not.toMatch(/Transcribe on device|在设备上转写/);
    screen.getByRole("button", { name: language === "zh-CN" ? "返回内容" : "Back to Content" }).click();
    document.body.innerHTML = "";
  }
});