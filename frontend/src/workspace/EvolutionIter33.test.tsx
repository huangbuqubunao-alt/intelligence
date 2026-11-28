import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import {
  buildTopicMarkdownWithPersonalNotes,
  TopicObsidianExportBar,
  type TopicAiEvolution,
} from "./WorkspaceAiWidgets";
import { savePersonalNote } from "./personalNotes";
import { UiLanguageProvider } from "./uiLanguage";

function sampleTopicEvolution(): TopicAiEvolution {
  return {
    video_count: 2,
    must_watch_count: 2,
    unread_count: 1,
    recent_7d_count: 2,
    avg_score: 9.1,
    latest_published_at: "2026-11-27T08:00:00Z",
    source_channels: ["Atlas Lab"],
    latest_headline_zh: "确定性状态机演进脉络",
    synthesis_zh: "专题综合理解",
    independence_summary_zh: "跨来源交叉印证",
    top_opportunities_zh: [],
    related_topics: [],
    channel_breakdown: [],
    source_perspectives: [],
    entries: [
      {
        video_id: "vidTop1",
        title: "Deterministic [Agent] | Architecture",
        channel_name: "Atlas Lab",
        published_at: "2026-11-27T08:00:00Z",
        score: 9.4,
        recommendation_tier: "MUST_WATCH",
        source_basis: "TRANSCRIPT",
        headline_zh: "核心架构与工具校验",
        summary_zh: "核心摘要",
        product_opportunities_zh: [],
        business_opportunities_zh: [],
      },
      {
        video_id: "vidTop2",
        title: "Unannotated Companion Video",
        channel_name: "Atlas Lab",
        published_at: "2026-11-26T08:00:00Z",
        score: 8.8,
        recommendation_tier: "MUST_WATCH",
        source_basis: "TRANSCRIPT",
        headline_zh: "对照组视频结论",
        summary_zh: "对照组摘要",
        product_opportunities_zh: [],
        business_opportunities_zh: [],
      },
    ],
    obsidian_markdown: "# AI Agent 架构\n\n## 专题综合\n既有双链主体",
  };
}

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 33 — Topics personal notes integration & augmented MOC export", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("yia.onboarding_completed.v1", "1");
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    window.location.hash = "";
  });

  it("leaves markdown untouched on 0 matched notes and appends sanitized personal notes when matched", () => {
    const evo = sampleTopicEvolution();
    const emptyRes = buildTopicMarkdownWithPersonalNotes(evo.obsidian_markdown!, evo, true);
    expect(emptyRes.matchedNoteCount).toBe(0);
    expect(emptyRes.markdown).toBe(evo.obsidian_markdown);

    savePersonalNote("vidTop1", {
      text: "Important personal validation note",
      tags: ["核心结论", "Agent"],
    });
    const matchedRes = buildTopicMarkdownWithPersonalNotes(evo.obsidian_markdown!, evo, true);
    expect(matchedRes.matchedNoteCount).toBe(1);
    expect(matchedRes.markdown).toContain("## 个人思考与批注 (1)");
    expect(matchedRes.markdown).toContain("### [[Deterministic Agent Architecture]] — #核心结论 #Agent");
    expect(matchedRes.markdown).toContain("Important personal validation note");
  });

  it("wires TopicObsidianExportBar personal-notes toggle cleanly to download and preview", async () => {
    savePersonalNote("vidTop1", {
      text: "Persisted topic synthesis insight",
      tags: ["状态机"],
    });

    const evo = sampleTopicEvolution();
    let exportedBlob: Blob | null = null;
    const origCreateObjectURL = URL.createObjectURL;
    const origRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn((blob: Blob) => {
      exportedBlob = blob;
      return "blob:topic-moc";
    });
    URL.revokeObjectURL = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <TopicObsidianExportBar
          topicName="AI Agent 架构"
          obsidianMarkdown={evo.obsidian_markdown!}
          evolution={evo}
        />
      </UiLanguageProvider>,
    );

    const checkbox = screen.getByRole("checkbox", { name: "附带本专题个人批注 (1)" }) as HTMLInputElement;
    expect(checkbox.checked).toBe(true);

    await user.click(screen.getByRole("button", { name: "下载专题 .md" }));
    expect(exportedBlob).not.toBeNull();
    const withNotes = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
      reader.readAsText(exportedBlob!);
    });
    expect(withNotes).toContain("Persisted topic synthesis insight");

    await user.click(checkbox);
    expect(checkbox.checked).toBe(false);
    await user.click(screen.getByRole("button", { name: "下载专题 .md" }));
    const withoutNotes = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
      reader.readAsText(exportedBlob!);
    });
    expect(withoutNotes).toBe(evo.obsidian_markdown);

    clickSpy.mockRestore();
    URL.createObjectURL = origCreateObjectURL;
    URL.revokeObjectURL = origRevokeObjectURL;
  });

  it("renders 已批注 badge and personal note excerpt on matching entries inside #Topics detail", async () => {
    savePersonalNote("vidTop1", {
      text: "Inline note excerpt visible in Topic detail card",
      tags: ["专题联动"],
    });
    window.location.hash = "#Topics";

    const evo = sampleTopicEvolution();
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/system") {
          return jsonResponse({ health: "ready", edition: "LOCAL" });
        }
        if (path === "/api/v1/topics") {
          return jsonResponse({
            topics: [
              {
                topic_id: "topAgent",
                name: "AI Agent 架构",
                current_state: "CONFIRMED",
                pinned: true,
                independence: "INDEPENDENT",
                ai_evolution: evo,
              },
            ],
          });
        }
        if (path === "/api/v1/topics/topAgent") {
          return jsonResponse({
            topic: {
              topic_id: "topAgent",
              name: "AI Agent 架构",
              current_state: "CONFIRMED",
              pinned: true,
              independence: "INDEPENDENT",
              contributions: [],
              relations: [],
              ai_evolution: evo,
            },
          });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    const topicRow = await screen.findByRole("button", { name: /AI Agent 架构/ });
    await user.click(topicRow);

    await waitFor(() => {
      expect(screen.getByText("已批注")).toBeTruthy();
      expect(screen.getByText("Inline note excerpt visible in Topic detail card")).toBeTruthy();
      expect(screen.getByText("#专题联动")).toBeTruthy();
      expect(screen.getByRole("checkbox", { name: "附带本专题个人批注 (1)" })).toBeTruthy();
    });
  });
});
