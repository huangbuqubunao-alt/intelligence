import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { BilibiliImport } from "./BilibiliImport";
import { UiLanguageProvider } from "./uiLanguage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
it("imports only the supplied public video and exposes truthful no-caption Content", async () => {
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ import: {
    content_id: "bilibili-BV1xx411c7mD", processing_status: "CAPTION_UNAVAILABLE", reused: false,
  } }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><BilibiliImport onClose={() => {}} onSaved={() => {}} onProvider={() => {}} /></UiLanguageProvider>);
  await userEvent.type(screen.getByLabelText("Bilibili video URL or BV id"), "BV1xx411c7mD");
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Import public video" }));
  await screen.findByText("Public captions are unavailable");
  expect(screen.getByRole("link", { name: "Open Content" }).getAttribute("href")).toBe("#Content/bilibili-BV1xx411c7mD");
  expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ input: "BV1xx411c7mD" });
  expect(fetch.mock.calls[0][0]).toBe("/api/v1/bilibili/imports");
  expect(screen.getByText(/Summary and Evidence require trusted captions/)).toBeTruthy();
});
it("localizes access denial and permits a bounded user retry", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const fetch = vi.fn().mockResolvedValue({ ok: false, json: async () => ({ error: { code: "BILIBILI_ACCESS_DENIED", message: "RAW BACKEND ENGLISH" } }) });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><BilibiliImport onClose={() => {}} onSaved={() => {}} onProvider={() => {}} /></UiLanguageProvider>);
  await userEvent.type(screen.getByLabelText("哔哩哔哩视频链接或 BV 号"), "BV1xx411c7mD");
  await userEvent.click(screen.getByRole("button", { name: "导入公开视频" }));
  expect((await screen.findByRole("alert")).textContent).toContain("无法公开访问");
  expect(screen.queryByText("RAW BACKEND ENGLISH")).toBeNull();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("button", { name: "导入公开视频" }).hasAttribute("disabled")).toBe(false);
});
