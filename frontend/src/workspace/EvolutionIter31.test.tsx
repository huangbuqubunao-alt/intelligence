import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { savePersonalNote } from "./personalNotes";
import { buildVerifiedIntelligenceMarkdown } from "./intelligenceExport";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 31 — Intelligence noted-only filter & verified Markdown export", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("yia.onboarding_completed.v1", "1");
    window.location.hash = "#Intelligence";
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    window.location.hash = "";
  });

  it("excludes untrusted or unavailable entries and embeds local personal notes in buildVerifiedIntelligenceMarkdown", () => {
    savePersonalNote("vidVerified1", {
      text: "Production takeaway for state machines",
      tags: ["核心结论", "状态机"],
    });

    const out = buildVerifiedIntelligenceMarkdown(
      [
        {
          status: "AVAILABLE",
          trusted: true,
          intelligence_id: "int1",
          effective_published_at: "2026-11-27T08:00:00Z",
          linked_topics: [{ topic_id: "t1", name: "AI Agent 架构" }],
          card: {
            core_conclusion: "确定性状态机优于开放循环",
            user_relevant_information: ["工具边界需强校验"],
            important_new_information: ["先锁字幕哈希再绑定引用"],
            meaningful_details: [],
            source_display_name: "Atlas Lab",
            video_id: "vidVerified1",
            video_title: "State [Machines] | Guide",
            evidence_links: [
              {
                evidence_id: "e1",
                translated_excerpt: "Always validate schema boundaries deterministically.",
              },
            ],
          },
        },
        {
          status: "AVAILABLE",
          trusted: false,
          intelligence_id: "intUntrusted",
          card: {
            core_conclusion: "SHOULD NOT EXPORT UNTRUSTED",
            user_relevant_information: [],
            important_new_information: [],
            meaningful_details: [],
            source_display_name: "Noise",
            video_id: "vidUntrusted",
            video_title: "Untrusted Video",
            evidence_links: [],
          },
        },
        {
          status: "UNAVAILABLE",
          trusted: true,
          intelligence_id: "intUnavail",
          card: {
            core_conclusion: "SHOULD NOT EXPORT UNAVAILABLE",
            user_relevant_information: [],
            important_new_information: [],
            meaningful_details: [],
            source_display_name: "Noise",
            video_id: "vidUnavail",
            video_title: "Unavailable Video",
            evidence_links: [],
          },
        },
      ],
      true,
      "仅看已批注",
    );

    expect(out.itemCount).toBe(1);
    expect(out.notedCount).toBe(1);
    expect(out.markdown).toContain("## [[State Machines Guide]]");
    expect(out.markdown).toContain("**核心判断**：确定性状态机优于开放循环");
    expect(out.markdown).toContain("### 个人批注 (#核心结论 #状态机)");
    expect(out.markdown).toContain("Production takeaway for state machines");
    expect(out.markdown).not.toContain("SHOULD NOT EXPORT");
  });

  it("filters Intelligence by 仅看已批注 (N) and exports verified insights Markdown", async () => {
    savePersonalNote("vidInt1", {
      text: "My personal annotation on vidInt1",
      tags: ["实践复盘"],
    });

    let exportedBlob: Blob | null = null;
    const origCreateObjectURL = URL.createObjectURL;
    const origRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn((blob: Blob) => {
      exportedBlob = blob;
      return "blob:intel-md";
    });
    URL.revokeObjectURL = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/system") {
          return jsonResponse({
            health: "ready",
            edition: "LOCAL",
            intelligence_model_status: "READY",
          });
        }
        if (path === "/api/v1/intelligence") {
          return jsonResponse({
            intelligence: [
              {
                intelligence_id: "int1",
                status: "AVAILABLE",
                trusted: true,
                state: "NEW",
                effective_published_at: "2026-11-27T08:00:00Z",
                linked_topics: [{ topic_id: "top1", name: "Agent" }],
                card: {
                  core_conclusion: "已批注的核心洞察结论 Alpha",
                  user_relevant_information: ["关键要点 Alpha"],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "src1",
                  source_display_name: "Atlas Lab",
                  source_url: null,
                  video_id: "vidInt1",
                  video_title: "Video Alpha",
                  original_video_url: null,
                  evidence_links: [{ evidence_id: "e1" }],
                },
              },
              {
                intelligence_id: "int2",
                status: "AVAILABLE",
                trusted: true,
                state: "NEW",
                effective_published_at: "2026-11-26T08:00:00Z",
                linked_topics: [{ topic_id: "top1", name: "Agent" }],
                card: {
                  core_conclusion: "未批注的对照组结论 Beta",
                  user_relevant_information: ["关键要点 Beta"],
                  important_new_information: [],
                  meaningful_details: [],
                  source_id: "src1",
                  source_display_name: "Atlas Lab",
                  source_url: null,
                  video_id: "vidInt2",
                  video_title: "Video Beta",
                  original_video_url: null,
                  evidence_links: [{ evidence_id: "e2" }],
                },
              },
            ],
            activity: [],
          });
        }
        if (path === "/api/v1/saved-intelligence") {
          return jsonResponse({ saved: [] });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("已批注的核心洞察结论 Alpha")).toBeTruthy();
    expect(screen.getByText("未批注的对照组结论 Beta")).toBeTruthy();

    const notedToggle = screen.getByRole("button", { name: "仅看已批注 (1)" });
    await user.click(notedToggle);

    expect(notedToggle.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("已批注的核心洞察结论 Alpha")).toBeTruthy();
    expect(screen.queryByText("未批注的对照组结论 Beta")).toBeNull();
    expect(screen.getByText("当前筛选命中 1 / 2 张验证洞察")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: "导出 Markdown (.md)" }));

    await waitFor(() => {
      expect(screen.getByText("已导出 Markdown (.md · 1 条)。")).toBeTruthy();
    });
    expect(exportedBlob).not.toBeNull();
    const mdText = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
      reader.readAsText(exportedBlob!);
    });
    expect(mdText).toContain("## [[Video Alpha]]");
    expect(mdText).toContain("My personal annotation on vidInt1");
    expect(mdText).not.toContain("未批注的对照组结论 Beta");
    clickSpy.mockRestore();
    URL.createObjectURL = origCreateObjectURL;
    URL.revokeObjectURL = origRevokeObjectURL;
  });
});
