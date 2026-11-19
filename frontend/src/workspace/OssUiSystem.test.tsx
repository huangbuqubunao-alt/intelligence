import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { commandScore } from "./ui/CommandPalette";
import { PhosphorIcon } from "./ui/phosphorIcons";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  location.hash = "";
});

describe("Phosphor Icons MIT adaptation (phosphor-icons/core)", () => {
  it("renders official 256x256 Phosphor vector paths in regular and fill weights as decorative SVGs", () => {
    const { container } = render(
      <div>
        <PhosphorIcon name="sparkle" weight="regular" />
        <PhosphorIcon name="sparkle" weight="fill" />
      </div>,
    );
    const svgs = container.querySelectorAll("svg");
    expect(svgs).toHaveLength(2);
    expect(svgs[0].getAttribute("viewBox")).toBe("0 0 256 256");
    expect(svgs[0].getAttribute("aria-hidden")).toBe("true");
    expect(svgs[0].getAttribute("data-weight")).toBe("regular");
    expect(svgs[1].getAttribute("data-weight")).toBe("fill");
    expect(svgs[0].innerHTML).not.toBe(svgs[1].innerHTML);
  });
});

describe("shadcn/ui Dual-Theme controller (Obsidian Dark & Warm Paper Light)", () => {
  beforeEach(() => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content";
    vi.stubGlobal("fetch", vi.fn(async (input: string) => ({
      ok: true,
      status: 200,
      json: async () => input.endsWith("/videos") ? { videos: [] } : {},
    } as Response)));
  });

  it("defaults to Obsidian Dark theme, toggles to Warm Paper Light with localStorage persistence, and keeps Home as first Tab stop", async () => {
    const user = userEvent.setup();
    render(<App />);
    expect(document.documentElement.dataset.theme).toBe("dark");

    // Keyboard contract: first Tab stop MUST remain Primary navigation -> Home
    await user.tab();
    const nav = screen.getByRole("navigation", { name: "主导航" });
    expect(document.activeElement).toBe(within(nav).getByRole("button", { name: "首页" }));
    const activeContentBtn = within(nav).getByRole("button", { name: "内容" });
    expect(activeContentBtn.querySelector("svg")?.getAttribute("data-weight")).toBe("fill");
    expect(within(nav).getByRole("button", { name: "首页" }).querySelector("svg")?.getAttribute("data-weight")).toBe("regular");

    const toggleBtn = screen.getByRole("button", { name: /切换为浅色暖纸主题|切换主题/ });
    await user.click(toggleBtn);
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(localStorage.getItem("yia.ui-theme")).toBe("light");

    await user.click(screen.getByRole("button", { name: /切换为深色黑曜石主题|切换主题/ }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("yia.ui-theme")).toBe("dark");
  });
});

describe("cmdk Command Palette (dip/cmdk adaptation)", () => {
  it("scores prefix, word-jump, and CJK substring matches accurately via commandScore", () => {
    const exactPrefix = commandScore("Agentic Workflow Architecture", "agent", ["youtube"]);
    const scattered = commandScore("A Good Evening In Tokyo", "agent", []);
    const miss = commandScore("Completely Unrelated Title", "quantum", []);
    const cjkHit = commandScore("大模型推理架构深度拆解", "推理架构", ["YouTube"]);

    expect(exactPrefix).toBeGreaterThan(scattered);
    expect(scattered).toBeGreaterThan(0);
    expect(miss).toBe(0);
    expect(cjkHit).toBeGreaterThan(0.7);
  });

  it("opens on Ctrl+K / Meta+K, fuzzy-filters workspace destinations and videos, and navigates via keyboard", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Home";
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body } as Response);
      if (input.endsWith("/videos")) {
        return ok({
          videos: [
            { video_id: "vid-alpha", provider: "YOUTUBE", channel_id: "c1", channel_name: "Latent Space", title: "Speculative Decoding Deep Dive", published_at: "2026-11-10T00:00:00Z", processing_status: "ANALYZED", last_updated: "2026-11-10T00:00:00Z" },
            { video_id: "vid-beta", provider: "LOCAL", channel_id: null, channel_name: null, title: "本地会议纪要整理", published_at: "2026-11-11T00:00:00Z", processing_status: "COMPLETED", last_updated: "2026-11-11T00:00:00Z" },
          ],
        });
      }
      if (input.includes("/videos/vid-alpha")) {
        return ok({
          video: { video_id: "vid-alpha", provider: "YOUTUBE", channel_id: "c1", channel_name: "Latent Space", title: "Speculative Decoding Deep Dive", published_at: "2026-11-10T00:00:00Z", processing_status: "ANALYZED", last_updated: "2026-11-10T00:00:00Z" },
          transcript: { status: "AVAILABLE", text: "Hello world" },
          note: { v2: { status: "AVAILABLE", method: "SOURCE_EXCERPTS", summary: "Clean summary", core_points: [], timestamped_key_points: [], evidence_references: [] } },
          intelligence_result: { status: "NOT_PROCESSED", has_new_intelligence: false, intelligence_id: null, revision_id: null, updated_at: "2026-11-10T00:00:00Z" },
          history: [],
        });
      }
      if (input.endsWith("/dashboard")) {
        return ok({ intelligence: [], pinned_topics: [], needs_attention: [], operations: { source_count: 1 } });
      }
      if (input.endsWith("/knowledge-delta")) {
        return ok({ knowledge_delta: { window_start: "2026-11-05T00:00:00Z", window_end: "2026-11-12T00:00:00Z", timezone: "Asia/Shanghai", status: "available", detail_limit: 2, categories: [] } });
      }
      if (input.endsWith("/intelligence")) return ok({ intelligence: [] });
      if (input.endsWith("/topics")) return ok({ topics: [] });
      if (input.endsWith("/evidence")) return ok({ evidence: [] });
      if (input.endsWith("/deep-analysis")) {
        return ok({ deep_analysis: { status: { availability: "NOT_QUALIFIED", reason_code: "NO_QUALIFIED_MODEL", reason: null, route_id: null, model_id: null, provider_id: null, qualified: false, consent_required: false }, result: null } });
      }
      return ok({});
    }));

    const user = userEvent.setup();
    render(<App />);

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const dialog = await screen.findByRole("dialog", { name: /全局搜索与命令面板/ });
    expect(dialog).toBeTruthy();

    const searchInput = within(dialog).getByRole("combobox");
    await user.type(searchInput, "Speculative");

    const option = await within(dialog).findByRole("option", { name: /Speculative Decoding Deep Dive/ });
    expect(option).toBeTruthy();

    await user.keyboard("{Enter}");
    expect(location.hash).toBe("#Content/vid-alpha");
    expect(screen.queryByRole("dialog", { name: /全局搜索与命令面板/ })).toBeNull();
  });
});

describe("Content library search/filter toolbar & Reader sticky section jump bar", () => {
  beforeEach(() => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body } as Response);
      if (input.endsWith("/videos")) {
        return ok({
          videos: [
            { video_id: "yt-1", provider: "YOUTUBE", channel_id: "c1", channel_name: "Andrej Karpathy", title: "LLM OS Lecture", published_at: "2026-11-10T00:00:00Z", processing_status: "ANALYZED", last_updated: "2026-11-10T00:00:00Z" },
            { video_id: "loc-1", provider: "LOCAL", channel_id: null, channel_name: null, title: "季度战略复盘录音.m4a", published_at: "2026-11-11T00:00:00Z", processing_status: "COMPLETED", last_updated: "2026-11-11T00:00:00Z" },
          ],
        });
      }
      if (input.includes("/videos/yt-1")) {
        return ok({
          video: { video_id: "yt-1", provider: "YOUTUBE", channel_id: "c1", channel_name: "Andrej Karpathy", title: "LLM OS Lecture", published_at: "2026-11-10T00:00:00Z", processing_status: "ANALYZED", last_updated: "2026-11-10T00:00:00Z" },
          transcript: { status: "AVAILABLE", text: "Clean transcript body" },
          note: { v2: { status: "AVAILABLE", method: "SOURCE_EXCERPTS", summary: "Clean summary body", core_points: [], timestamped_key_points: [], evidence_references: [] } },
          intelligence_result: { status: "NOT_PROCESSED", has_new_intelligence: false, intelligence_id: null, revision_id: null, updated_at: "2026-11-10T00:00:00Z" },
          history: [],
        });
      }
      if (input.endsWith("/evidence")) return ok({ evidence: [] });
      if (input.endsWith("/deep-analysis")) {
        return ok({ deep_analysis: { status: { availability: "NOT_QUALIFIED", reason_code: "NO_QUALIFIED_MODEL", reason: null, route_id: null, model_id: null, provider_id: null, qualified: false, consent_required: false }, result: null } });
      }
      return ok({});
    }));
  });

  it("filters Content list by search query and provider chip while showing all items by default, and renders sticky section jump bar in Reader", async () => {
    location.hash = "#Content";
    const user = userEvent.setup();
    render(<App />);

    // Both items visible by default
    expect(await screen.findByText("LLM OS Lecture")).toBeTruthy();
    expect(screen.getByText("季度战略复盘录音.m4a")).toBeTruthy();

    // Filter by search query
    const filterInput = screen.getByRole("searchbox", { name: /搜索内容库/ });
    await user.type(filterInput, "战略复盘");
    expect(screen.queryByText("LLM OS Lecture")).toBeNull();
    expect(screen.getByText("季度战略复盘录音.m4a")).toBeTruthy();

    await user.clear(filterInput);
    expect(screen.getByText("LLM OS Lecture")).toBeTruthy();

    // Open reader -> verify sticky section jump bar AND DOM order (Intelligence result before Transcript)
    await user.click(screen.getByText("LLM OS Lecture"));
    const jumpNav = await screen.findByRole("toolbar", { name: "章节速跳" });
    const intelJump = within(jumpNav).getByRole("button", { name: /洞察处理结果/ });
    const summaryJump = within(jumpNav).getByRole("button", { name: /摘要/ });
    expect(intelJump.getAttribute("aria-current")).toBe("location");
    expect(summaryJump.getAttribute("aria-current")).toBeNull();
    expect(within(jumpNav).getByRole("button", { name: /原始字幕/ })).toBeTruthy();

    await user.click(summaryJump);
    expect(summaryJump.getAttribute("aria-current")).toBe("location");
    expect(intelJump.getAttribute("aria-current")).toBeNull();

    const headings = screen.getAllByRole("heading", { level: 2 }).map(el => el.textContent);
    const intelIdx = headings.findIndex(text => text?.includes("洞察处理结果"));
    const transcriptIdx = headings.findIndex(text => text?.includes("原始字幕"));
    expect(intelIdx).toBeGreaterThan(-1);
    expect(transcriptIdx).toBeGreaterThan(intelIdx);
  });

  it("navigates directly to Topic detail when clicking a Pinned Topic pill on the Home workbench rail", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Home";
    vi.stubGlobal("fetch", vi.fn(async (input: string) => {
      const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body } as Response);
      if (input.endsWith("/dashboard")) {
        return ok({
          intelligence: [],
          pinned_topics: [
            { topic_id: "topic-reasoning", name: "AI 推理可靠性与核验", pinned: true, lifecycle: "ACTIVE", current_state: "CONFIRMED", independence: "INDEPENDENT", contributions: [], timeline: [] },
          ],
          needs_attention: [],
          operations: { source_count: 1 },
        });
      }
      if (input.endsWith("/knowledge-delta")) {
        return ok({ knowledge_delta: { window_start: "2026-11-05T00:00:00Z", window_end: "2026-11-12T00:00:00Z", timezone: "Asia/Shanghai", status: "available", detail_limit: 2, categories: [] } });
      }
      if (input.endsWith("/topics")) {
        return ok({
          topics: [
            { topic_id: "topic-reasoning", name: "AI 推理可靠性与核验", pinned: true, lifecycle: "ACTIVE", current_state: "CONFIRMED", independence: "INDEPENDENT", contributions: [], timeline: [] },
          ],
        });
      }
      if (input.includes("/topics/topic-reasoning")) {
        return ok({
          topic: { topic_id: "topic-reasoning", name: "AI 推理可靠性与核验", pinned: true, lifecycle: "ACTIVE", current_state: "CONFIRMED", independence: "INDEPENDENT", contributions: [], timeline: [], relations: [] },
        });
      }
      return ok({});
    }));

    const user = userEvent.setup();
    render(<App />);

    const pinnedBtn = await screen.findByRole("button", { name: /AI 推理可靠性与核验/ });
    await user.click(pinnedBtn);
    await waitFor(() => expect(location.hash).toBe("#Topics/topic-reasoning"));
    expect(await screen.findByRole("button", { name: /取消置顶主题|返回主题/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /时间线/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /关联主题/ })).toBeTruthy();
  });
});
