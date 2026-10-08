import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { AddEntry, recognizeLink } from "./AddEntry";
import { UiLanguageProvider } from "./uiLanguage";

const channel = "UC_x5XG1OV2P6uZZ5FSM9Ttw";
test.each(["@example", "https://www.youtube.com/@example", "https://www.youtube.com/@example/videos", channel, `https://www.youtube.com/channel/${channel}`])("recognizes canonical channel without provider calls: %s", input => {
  expect(recognizeLink(input)?.kind).toBe("YOUTUBE_CHANNEL");
  expect(recognizeLink(input)?.canonical).not.toMatch(/\/videos$/);
});
test.each(["https://www.youtube.com/watch?v=abcdefghijk", "https://youtu.be/abcdefghijk", "https://www.youtube.com/shorts/abcdefghijk", "https://www.youtube.com/live/abcdefghijk"])("recognizes one-time YouTube content: %s", input => expect(recognizeLink(input)).toEqual({ kind: "YOUTUBE_VIDEO", canonical: "https://www.youtube.com/watch?v=abcdefghijk" }));
test.each(["BV1xx411c7mD", "https://www.bilibili.com/video/BV1xx411c7mD/"])("recognizes public Bilibili content: %s", input => expect(recognizeLink(input)?.kind).toBe("BILIBILI_VIDEO"));
test.each(["https://youtube.com.evil.test/@example", "http://youtube.com/@example", "https://youtube.com/watch?v=bad", "https://b23.tv/short", "https://space.bilibili.com/123", "https://www.bilibili.com/video/BV1xx411c7mD/?p=2", "https://user@youtube.com/@example", "https://youtube.com/@example/evil"])("rejects unsupported or unsafe input: %s", input => expect(recognizeLink(input)).toBeNull());

test.each(["en", "zh-CN"])("one Add entry confirms default channel organization, optional extraction and local import (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  const fetchMock = vi.fn(async () => ({ ok: true, json: async () => ({ source: { tracking: {} } }) }));
  vi.stubGlobal("fetch", fetchMock);
  render(<UiLanguageProvider><AddEntry onClose={vi.fn()} onSaved={vi.fn()} /></UiLanguageProvider>);
  fireEvent.change(screen.getByLabelText(language === "en" ? "Paste link" : "粘贴链接"), { target: { value: "https://www.youtube.com/@example/videos" } });
  expect(screen.getByText(language === "en" ? /keep following future content/ : /持续关注未来新内容/)).toBeTruthy();
  expect((screen.getByRole("radio", { name: language === "en" ? /^Organize content/ : /^整理内容/ }) as HTMLInputElement).checked).toBe(true);
  expect(screen.queryByLabelText("Monitor this Source")).toBeNull();
  expect(screen.queryByLabelText("Enable automatic schedule")).toBeNull();
  expect(screen.getByRole("button", { name: language === "en" ? "Import local file" : "导入本地文件" })).toBeTruthy();
  expect(screen.getByRole("button", { name: language === "en" ? "Close" : "关闭" })).toBeTruthy();
  fireEvent.click(screen.getByRole("radio", { name: language === "en" ? /^Also extract Intelligence/ : /^进一步提炼洞察/ }));
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Follow channel" : "关注频道" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/v1/sources/channels", expect.objectContaining({ body: JSON.stringify({ input: "https://www.youtube.com/@example", processing_mode: "EXTRACT_INTELLIGENCE" }) })));
});

test("invalid input gives actionable copy and makes zero writes", () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
  render(<UiLanguageProvider><AddEntry onClose={vi.fn()} onSaved={vi.fn()} /></UiLanguageProvider>);
  fireEvent.change(screen.getByLabelText("Paste link"), { target: { value: "wrong link" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm import" }));
  expect(screen.getByRole("alert").textContent).toMatch(/supported HTTPS/);
  expect(screen.queryByText("Request values are invalid or unavailable.")).toBeNull();
  expect(fetchMock).not.toHaveBeenCalled();
});
