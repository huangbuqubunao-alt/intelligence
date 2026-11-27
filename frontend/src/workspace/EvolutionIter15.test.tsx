import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AddEntry, parseBatchLinks } from "./AddEntry";
import { UiLanguageProvider } from "./uiLanguage";
import { ApiRequestError } from "../api/client";

const { postMock } = vi.hoisted(() => ({
  postMock: vi.fn(),
}));

vi.mock("../api/client", async () => {
  const actual = await vi.importActual<typeof import("../api/client")>("../api/client");
  return {
    ...actual,
    post: postMock,
  };
});

describe("Iteration 15 — Batch Multi-Link Recognition & Queue Import", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("deduplicates mixed YouTube/Bilibili links, isolates invalid lines, and caps valid entries at 10", () => {
    const validTwelve = Array.from({ length: 12 }, (_, idx) => {
      const suffix = String(idx).padStart(2, "0");
      return `https://www.youtube.com/watch?v=abcDEF123${suffix}`;
    });
    const raw = [
      validTwelve[0],
      validTwelve[0], // duplicate canonical
      "https://www.bilibili.com/video/BV1xx411c7mD/?p=1",
      "@OpenAI",
      "http://insecure-example.com/bad",
      ...validTwelve.slice(1),
    ].join("\n");

    const parsed = parseBatchLinks(raw);
    expect(parsed.validItems).toHaveLength(10);
    expect(parsed.duplicateCount).toBe(1);
    expect(parsed.invalidCount).toBe(1);
    expect(parsed.truncatedCount).toBe(4);
    expect(parsed.validItems[0]?.recognized.kind).toBe("YOUTUBE_VIDEO");
    expect(parsed.validItems[1]?.recognized.kind).toBe("BILIBILI_VIDEO");
    expect(parsed.validItems[2]?.recognized.kind).toBe("YOUTUBE_CHANNEL");
  });

  it("auto-switches on multi-line paste and runs sequential queue import resiliently across partial failures", async () => {
    const user = userEvent.setup();
    postMock.mockImplementation(async (path: string) => {
      if (path === "/sources/import") {
        return { source: { video_id: "vidBatch1" } };
      }
      if (path === "/bilibili/imports") {
        throw new ApiRequestError({ code: "BILIBILI_UNAVAILABLE", message: "rate limited" });
      }
      if (path === "/sources/channels") {
        return { channel: { channel_id: "ch1" } };
      }
      return {};
    });

    render(
      <UiLanguageProvider>
        <AddEntry onClose={vi.fn()} onSaved={vi.fn()} />
      </UiLanguageProvider>,
    );

    const singleInput = screen.getByLabelText(/Paste link|粘贴链接/i);
    await user.click(singleInput);
    await user.paste(
      "https://www.youtube.com/watch?v=dQw4w9WgXcQ\nBV1xx411c7mD\n@anthropic-ai\nnot-a-valid-link",
    );

    const textarea = await screen.findByRole("textbox", { name: /Batch links|批量链接/i });
    expect(textarea).toBeTruthy();
    expect(screen.getByText(/YouTube 频道|YouTube channel/)).toBeTruthy();

    const submitBtn = screen.getByRole("button", { name: /Import batch \(3\)|开始批量导入 \(3\)/ });
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Batch complete: 2 succeeded, 1 failed|批量导入完成：2 条成功，1 条失败/)).toBeTruthy();
    });

    expect(postMock).toHaveBeenCalledTimes(3);
    expect(postMock).toHaveBeenNthCalledWith(
      1,
      "/sources/import",
      expect.objectContaining({ url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" }),
    );
    expect(postMock).toHaveBeenNthCalledWith(
      2,
      "/bilibili/imports",
      { input: "https://www.bilibili.com/video/BV1xx411c7mD/" },
    );
    expect(postMock).toHaveBeenNthCalledWith(
      3,
      "/sources/channels",
      { input: "https://www.youtube.com/@anthropic-ai", processing_mode: "ORGANIZE_CONTENT" },
    );
  });
});
