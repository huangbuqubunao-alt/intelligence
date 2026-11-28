import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { buildSelectedContentMarkdown } from "./contentExport";
import { batchAddPersonalTags, readPersonalNote, savePersonalNote } from "./personalNotes";

const origCreateObjectURL = URL.createObjectURL;
const origRevokeObjectURL = URL.revokeObjectURL;

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Iteration 36 (EVO-W7-01): #Content batch personal tagging & Obsidian reading pack export", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.onboarding_completed.v1", "1");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content";
  });

  afterEach(() => {
    cleanup();
    URL.createObjectURL = origCreateObjectURL;
    URL.revokeObjectURL = origRevokeObjectURL;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  it("batchAddPersonalTags merges new tags without overwriting existing note text or tags", () => {
    savePersonalNote("v1", { text: "已有深读体会", tags: ["Agent"] });
    const res = batchAddPersonalTags(["v1", "v2"], "#agent #必复盘 #工作流");

    expect(res.tagsAdded).toEqual(["agent", "必复盘", "工作流"]);
    expect(res.updatedCount).toBe(2);

    const n1 = readPersonalNote("v1");
    expect(n1?.text).toBe("已有深读体会");
    expect(n1?.tags).toEqual(["Agent", "必复盘", "工作流"]);

    const n2 = readPersonalNote("v2");
    expect(n2?.text).toBe("");
    expect(n2?.tags).toEqual(["agent", "必复盘", "工作流"]);
  });

  it("buildSelectedContentMarkdown formats wikilinks, AI scores, takeaways, and personal notes", () => {
    const result = buildSelectedContentMarkdown(
      [
        {
          item: {
            video_id: "v1",
            title: "Agent [Orchestration] Deep Dive",
            channel_name: "AI Lab",
            source_url: "https://youtube.com/watch?v=v1",
          },
          brief: {
            score: 9.2,
            recommendation_tier: "MUST_WATCH",
            headline_zh: "显式状态机比自由循环更可靠",
            summary_zh: "长链路必须限定状态迁移。",
            topic_cluster_zh: "AI Agent 工程架构",
            product_opportunities_zh: ["增加状态审计面板"],
            business_opportunities_zh: [],
          },
          note: {
            text: "下周对照项目落地状态机",
            tags: ["必复盘", "状态机"],
            updatedAt: "2026-11-27T08:00:00.000Z",
          },
        },
      ],
      true,
    );

    expect(result.count).toBe(1);
    expect(result.filename).toMatch(/^reading-pack-\d{4}-\d{2}-\d{2}\.md$/);
    expect(result.markdown).toContain("## [[Agent Orchestration Deep Dive]]");
    expect(result.markdown).toContain("AI 评分：9.2/10 (必看干货)");
    expect(result.markdown).toContain("[[AI Agent 工程架构]]");
    expect(result.markdown).toContain("- 增加状态审计面板");
    expect(result.markdown).toContain("#必复盘 #状态机");
    expect(result.markdown).toContain("下周对照项目落地状态机");
  });

  it("supports batch tagging and exporting a selected Obsidian reading pack from #Content", async () => {
    const blobs: Blob[] = [];
    URL.createObjectURL = vi.fn((blob: Blob | MediaSource) => {
      blobs.push(blob as Blob);
      return "blob:reading-pack";
    });
    URL.revokeObjectURL = vi.fn();

    vi.stubGlobal("fetch", (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/system")) {
        return okJson({ health: "ready", edition: "LOCAL" });
      }
      if (url.includes("/api/v1/settings/source-policy")) {
        return okJson({
          policy: {
            focus_rules: [],
            ignore_rules: [],
            distillation_style: "BALANCED",
            initial_history_count: 5,
            per_run_max_new_videos: 5,
          },
        });
      }
      if (url.includes("/api/v1/settings/preferences")) {
        return okJson({ active: [], history: [] });
      }
      if (url.includes("/api/v1/settings/resource-usage")) {
        return okJson({ usage: [] });
      }
      if (url.includes("/api/v1/settings")) {
        return okJson({
          general: { output_language: "zh-CN", output_language_updated_at: null },
          providers: [],
        });
      }
      if (url.includes("/api/v1/sources")) {
        return okJson({ sources: [] });
      }
      if (url.includes("/api/v1/topics")) {
        return okJson({ topics: [] });
      }
      if (url.includes("/api/v1/videos")) {
        return okJson({
          videos: [
            {
              video_id: "vid1",
              channel_id: "ch1",
              title: "状态机驱动的多智能体设计",
              channel_name: "Builder Channel",
              provider: "YOUTUBE",
              processing_status: "READY",
              published_at: "2026-11-25T10:00:00Z",
              last_updated: "2026-11-25T10:00:00Z",
              duration_seconds: 1200,
              source_url: "https://youtube.com/watch?v=vid1",
              ai_brief: {
                video_id: "vid1",
                headline_zh: "核心结论：显式状态机可控可测",
                summary_zh: "总结正文",
                score: 9.1,
                score_reason_zh: "干货密集",
                recommendation_tier: "MUST_WATCH",
                content_bucket: "DEEP_DIVE",
                is_short_noise: false,
                starred: false,
                is_read: false,
                topics_zh: ["Agent"],
                topic_cluster_zh: "AI Agent 工程架构",
                product_opportunities_zh: ["提供状态回放视图"],
                business_opportunities_zh: [],
              },
            },
          ],
          total: 1,
          has_more: false,
        });
      }
      return okJson({});
    });

    render(<App />);

    const selectBtn = await screen.findByRole("button", { name: /多选对比/ });
    fireEvent.click(selectBtn);

    const checkbox = await screen.findByRole("checkbox", {
      name: /选择：状态机驱动的多智能体设计/,
    });
    fireEvent.click(checkbox);

    fireEvent.click(screen.getByRole("button", { name: /批量打标签/ }));
    const tagInput = screen.getByLabelText("输入批量个人标签");
    fireEvent.change(tagInput, { target: { value: "#精选汇编 #架构" } });
    fireEvent.click(screen.getByRole("button", { name: "应用标签" }));

    await waitFor(() => {
      expect(screen.getByText(/已为 1 篇内容应用标签：#精选汇编 #架构/)).toBeTruthy();
    });
    expect(readPersonalNote("vid1")?.tags).toEqual(["精选汇编", "架构"]);

    fireEvent.click(screen.getByRole("button", { name: /导出精选 \(\.md\)/ }));
    await waitFor(() => {
      expect(screen.getByText(/已导出精选阅读包 \(\.md · 1 篇\)/)).toBeTruthy();
    });
    expect(blobs.length).toBeGreaterThanOrEqual(1);
    const exportedText = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
      reader.readAsText(blobs[blobs.length - 1]);
    });
    expect(exportedText).toContain("## [[状态机驱动的多智能体设计]]");
    expect(exportedText).toContain("#精选汇编 #架构");
  });
});
