import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

const scrollIntoView = vi.fn();
const originalScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  location.hash = "#Content";
  localStorage.setItem("yia.ui-language", "en");
  Object.defineProperty(HTMLElement.prototype, "scrollIntoView", { configurable: true, value: scrollIntoView });
  scrollIntoView.mockClear();
  fetchMock = vi.fn((path: string) => Promise.resolve({ ok: true, json: async () => path.endsWith("/videos")
    ? { videos: [] }
    : path.endsWith("/sources") ? { sources: [] }
    : path.endsWith("/settings") ? { bilibili: { creator_following: { available: false } } }
    : {} }));
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  if (originalScroll) Object.defineProperty(HTMLElement.prototype, "scrollIntoView", originalScroll);
  else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
  location.hash = "";
});

it.each(["en", "zh-CN"])("reveals each overflowing primary destination on Tab and Shift+Tab without activating it (%s)", async language => {
  localStorage.setItem("yia.ui-language", language);
  const user = userEvent.setup();
  render(<App />);
  const nav = screen.getByRole("navigation", { name: language === "en" ? "Primary navigation" : "主导航" });
  const buttons = within(nav).getAllByRole("button");
  expect(buttons).toHaveLength(6);
  Object.defineProperties(nav, { clientWidth: { value: 277 }, scrollWidth: { value: 467 } });
  await screen.findByText(language === "en" ? "No Content yet. Add a video link, follow a YouTube channel, or import a local file." : "暂无内容。添加视频链接，持续关注 YouTube 频道，或导入本地文件。");
  const originalHash = location.hash;
  for (const button of buttons) {
    await user.tab();
    expect(document.activeElement).toBe(button);
    expect(scrollIntoView.mock.instances.at(-1)).toBe(button);
    expect(scrollIntoView).toHaveBeenLastCalledWith({ block: "nearest", inline: "nearest" });
    expect(location.hash).toBe(originalHash);
  }
  await user.tab(); // Leave the nav, then traverse all six destinations backwards.
  for (const button of [...buttons].reverse()) {
    await user.tab({ shift: true });
    expect(document.activeElement).toBe(button);
    expect(scrollIntoView.mock.instances.at(-1)).toBe(button);
    expect(location.hash).toBe(originalHash);
  }
  expect(scrollIntoView).toHaveBeenCalledTimes(12);
  expect(fetchMock.mock.calls.every(([, init]) => !init || !(init as RequestInit).method || (init as RequestInit).method === "GET")).toBe(true);
  await user.tab(); // Following still activates only when the user presses Enter.
  await user.keyboard("{Enter}");
  expect(location.hash).toBe("#Following");
  expect(await screen.findByRole("heading", { name: language === "en" ? "Following" : "关注" })).toBeTruthy();
});

it("leaves non-overflowing navigation and mouse activation unchanged", async () => {
  const user = userEvent.setup();
  render(<App />);
  const nav = screen.getByRole("navigation", { name: "Primary navigation" });
  Object.defineProperties(nav, { clientWidth: { value: 220 }, scrollWidth: { value: 220 } });
  await user.tab();
  expect(document.activeElement).toBe(within(nav).getByRole("button", { name: "Home" }));
  expect(scrollIntoView).not.toHaveBeenCalled();
  await user.click(within(nav).getByRole("button", { name: "Following" }));
  expect(location.hash).toBe("#Following");
  expect(await screen.findByRole("heading", { name: "Following" })).toBeTruthy();
  expect(scrollIntoView).not.toHaveBeenCalled();
});
