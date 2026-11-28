import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { buildPastedMarkdownPayload, derivePasteFilename } from "./QuickPasteNoteForm";

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  localStorage.setItem("intelligence.onboarding.completed.demo.v1", "true");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  location.hash = "";
});

it("derives clean Markdown filenames and formats pasted payload safely", () => {
  expect(derivePasteFilename("My Architecture Review!", "body text")).toBe("My-Architecture-Review!.md");
  expect(derivePasteFilename("", "# Team Sync Notes\nDetails")).toBe("Team-Sync-Notes.md");
  expect(derivePasteFilename("", "###")).toMatch(/^pasted-note-\d{8}-\d{4}\.md$/);

  expect(buildPastedMarkdownPayload("Title", "Paragraph one")).toBe("# Title\n\nParagraph one\n");
  expect(buildPastedMarkdownPayload("Title", "# Already Headed\nBody")).toBe("# Already Headed\nBody\n");
  expect(buildPastedMarkdownPayload("OnlyTitle", "   ")).toBe("");
});

it("opens Quick Paste Markdown modal from Cmd+K, uploads to /local/imports, and opens Document Reader", async () => {
  location.hash = "#Home";
  const postCalls: { url: string; method: string; headers?: unknown }[] = [];

  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    if (method === "POST") {
      postCalls.push({ url: path, method, headers: init?.headers });
      if (path.startsWith("/api/v1/local/imports?")) {
        return jsonResponse(
          {
            import: {
              content_id: "local-pasted-1",
              filename: "Agent-架构纪要.md",
              status: "READY",
              duplicate: false,
            },
          },
          201,
        );
      }
    }
    if (path === "/api/v1/videos/local-pasted-1") {
      return jsonResponse({
        video: {
          video_id: "local-pasted-1",
          title: "Agent-架构纪要.md",
          provider: "LOCAL",
          media_kind: "TEXT",
          channel_id: "local",
          channel_name: "Local",
          processing_status: "READY",
          imported_at: "2026-11-27T09:30:00Z",
        },
        transcript: {
          status: "AVAILABLE",
          text: "# Agent 架构纪要\n\n采用状态机保证恢复。",
        },
        note: { v2: { status: "NOT_AVAILABLE" } },
        intelligence_result: { status: "NOT_AVAILABLE" },
        history: [],
        workspace_ai_capabilities: { ready: true, transcriber_ready: false },
      });
    }
    if (path.endsWith("/evidence")) return jsonResponse({ evidence: [] });
    if (path.endsWith("/deep-analysis")) {
      return jsonResponse({
        deep_analysis: {
          status: {
            availability: "NOT_QUALIFIED",
            reason_code: "NO_QUALIFIED_MODEL",
            qualified: false,
            production_eligible: false,
            consent_required: false,
            routes: [],
          },
          result: null,
        },
      });
    }
    return jsonResponse({});
  });
  vi.stubGlobal("fetch", fetchMock);

  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByRole("button", { name: /搜索与直达/ }));
  await user.click(await screen.findByText("粘贴文本或笔记入库"));

  expect(await screen.findByRole("dialog", { name: "粘贴文本 / 笔记直接入库" })).toBeTruthy();

  const submitBtn = screen.getByRole("button", { name: "保存并打开阅读器" });
  expect((submitBtn as HTMLButtonElement).disabled).toBe(true);

  await user.type(screen.getByRole("textbox", { name: "笔记标题（可选）" }), "Agent 架构纪要");
  await user.type(
    screen.getByRole("textbox", { name: "粘贴正文内容" }),
    "采用状态机保证崩溃恢复。",
  );

  expect((submitBtn as HTMLButtonElement).disabled).toBe(false);
  await user.click(submitBtn);

  expect(postCalls.some((c) => c.url === `/api/v1/local/imports?filename=${encodeURIComponent("Agent-架构纪要.md")}`)).toBe(true);
  expect(await screen.findByRole("heading", { name: "Agent-架构纪要.md" })).toBeTruthy();
  expect(location.hash).toBe("#Content/local-pasted-1");
  expect(await screen.findByText("原文已就绪 · 待提炼洞察")).toBeTruthy();
});
