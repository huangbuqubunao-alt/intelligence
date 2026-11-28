import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function installFetchStub() {
  const fetchMock = vi.fn((path: string) => {
    if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
      return jsonResponse({
        videos: [
          {
            video_id: "vidUnread",
            title: "Unread Agent Playbook",
            provider: "YOUTUBE",
            channel_id: "UC1",
            channel_name: "Atlas",
            published_at: "2026-11-26T10:00:00Z",
            processing_status: "READY",
            last_updated: "2026-11-26T10:00:00Z",
            duration_seconds: 1200,
            ai_brief: {
              video_id: "vidUnread",
              headline_zh: "未读高优架构指南",
              summary_zh: "确定性工作流拆分方案。",
              score: 9.2,
              score_reason_zh: "高分指南",
              recommendation_tier: "MUST_WATCH",
              content_bucket: "DEEP_DIVE",
              is_short_noise: false,
              is_read: false,
              starred: false,
              topics_zh: ["Agent"],
              topic_cluster_zh: "AI Agent",
              product_opportunities_zh: [],
              business_opportunities_zh: [],
            },
          },
          {
            video_id: "vidAlreadyRead",
            title: "Already Read Video",
            provider: "YOUTUBE",
            channel_id: "UC1",
            channel_name: "Atlas",
            published_at: "2026-11-25T10:00:00Z",
            processing_status: "READY",
            last_updated: "2026-11-25T10:00:00Z",
            duration_seconds: 900,
            ai_brief: {
              video_id: "vidAlreadyRead",
              headline_zh: "已读旧视频",
              summary_zh: "常规评测。",
              score: 7.4,
              score_reason_zh: "值得一听",
              recommendation_tier: "WORTH_WATCHING",
              content_bucket: "DEEP_DIVE",
              is_short_noise: false,
              is_read: true,
              starred: false,
              topics_zh: ["Agent"],
              topic_cluster_zh: "AI Agent",
              product_opportunities_zh: [],
              business_opportunities_zh: [],
            },
          },
        ],
      });
    }
    if (path.endsWith("/intelligence")) {
      return jsonResponse({
        intelligence: [
          {
            intelligence_id: "int1",
            status: "AVAILABLE",
            state: "CONFIRMED",
            claim_kind: "SYSTEM_INFERENCE",
            trusted: true,
            evidence_ids: ["ev1"],
            card: {
              source_id: "UC1",
              video_id: "vidUnread",
              core_conclusion: "Separate deterministic ingestion from model inference.",
              video_title: "Unread Agent Playbook",
              source_display_name: "Atlas",
              user_relevant_information: ["Keep side effects outside unstructured loops."],
              important_new_information: ["SQLite checkpointing prevents duplicate writes."],
              evidence_links: [{ evidence_id: "ev1", label: "0:00-0:42" }],
            },
          },
        ],
      });
    }
    if (path.endsWith("/saved-intelligence")) {
      return jsonResponse({
        saved: [
          {
            intelligence_id: "int1",
            intelligence: {
              intelligence_id: "int1",
              status: "AVAILABLE",
              state: "CONFIRMED",
              claim_kind: "SYSTEM_INFERENCE",
              trusted: true,
              evidence_ids: ["ev1"],
            },
          },
        ],
      });
    }
    if (path.endsWith("/topics")) return jsonResponse({ topics: [] });
    if (path.endsWith("/sources")) return jsonResponse({ sources: [] });
    if (path.endsWith("/research/sessions")) return jsonResponse({ sessions: [] });
    return jsonResponse({});
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
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

it("renders the Intelligence mental-model strip and navigates cleanly to Content triage", async () => {
  location.hash = "#Intelligence";
  installFetchStub();
  const user = userEvent.setup();
  render(<App />);

  expect(
    await screen.findByText(/可复用判断库 · 共 1 条已核验洞察 · 1 条已收藏/),
  ).toBeTruthy();

  const cta = screen.getByRole("button", { name: "前往内容分诊 →" });
  await user.click(cta);

  expect(location.hash).toBe("#Content");
  expect(await screen.findByText("Unread Agent Playbook")).toBeTruthy();
});

it("opens ? Keyboard Shortcuts modal outside inputs, ignores ? inside inputs, restores focus on Esc, and keeps 6 nav items", async () => {
  location.hash = "#Content";
  installFetchStub();
  const user = userEvent.setup();
  render(<App />);

  await screen.findByText("Unread Agent Playbook");
  const nav = screen.getByRole("navigation", { name: "主导航" });
  expect(within(nav).getAllByRole("button")).toHaveLength(6);

  const searchInput = screen.getByRole("searchbox");
  await user.click(searchInput);
  await user.keyboard("?");
  expect(screen.queryByRole("dialog", { name: "键盘快捷键指南" })).toBeNull();

  const triggerBtn = screen.getByRole("button", { name: "键盘快捷键指南 (?)" });
  triggerBtn.focus();
  await user.keyboard("?");

  expect(screen.getByRole("dialog", { name: "键盘快捷键指南" })).toBeTruthy();
  await user.keyboard("{Escape}");
  await waitFor(() => {
    expect(screen.queryByRole("dialog", { name: "键盘快捷键指南" })).toBeNull();
  });
  expect(document.activeElement).toBe(triggerBtn);
});

it("jumps from Cmd+K power action Triage unread content into #Content with UNREAD bucket active", async () => {
  location.hash = "#Home";
  installFetchStub();
  const user = userEvent.setup();
  render(<App />);

  await user.click(await screen.findByRole("button", { name: /搜索与直达/ }));
  const unreadAction = await screen.findByText("高优未读内容分诊");
  await user.click(unreadAction);

  expect(location.hash).toBe("#Content");
  expect(await screen.findByText("Unread Agent Playbook")).toBeTruthy();
  expect(screen.queryByText("Already Read Video")).toBeNull();
});
