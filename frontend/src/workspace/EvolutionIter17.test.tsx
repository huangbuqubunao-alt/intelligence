import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { WorkspaceAiSettingsPanel } from "./WorkspaceAiWidgets";
import { savePersonalNote } from "./personalNotes";
import { UiLanguageProvider } from "./uiLanguage";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 17 — Annotated Content Filter & Personal Notes Backup/Restore", () => {
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

  it("shows Noted bucket filter in Content when personal notes exist and filters exclusively to noted entries", async () => {
    savePersonalNote("vidNoted1", {
      text: "Key architecture insight",
      tags: ["架构"],
    });
    location.hash = "#Content";
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/videos" || path.startsWith("/api/v1/videos?")) {
          return jsonResponse({
            videos: [
              {
                video_id: "vidNoted1",
                title: "Annotated Source Alpha",
                provider: "YOUTUBE",
                channel_id: "UC1",
                channel_name: "Alpha",
                published_at: "2026-11-27T08:00:00Z",
                processing_status: "READY",
                duration_seconds: 900,
                ai_brief: {
                  video_id: "vidNoted1",
                  headline_zh: "已写批注的视频",
                  summary_zh: "摘要一",
                  score: 9.0,
                  score_reason_zh: "高价值",
                  recommendation_tier: "MUST_WATCH",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["Agent"],
                  topic_cluster_zh: "Agent 架构",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
              {
                video_id: "vidPlain2",
                title: "Unnoted Source Beta",
                provider: "YOUTUBE",
                channel_id: "UC2",
                channel_name: "Beta",
                published_at: "2026-11-26T08:00:00Z",
                processing_status: "READY",
                duration_seconds: 900,
                ai_brief: {
                  video_id: "vidPlain2",
                  headline_zh: "尚未做笔记的视频",
                  summary_zh: "摘要二",
                  score: 8.5,
                  score_reason_zh: "参考",
                  recommendation_tier: "WORTH_SKIMMING",
                  content_bucket: "DEEP_DIVE",
                  is_short_noise: false,
                  starred: false,
                  is_read: false,
                  topics_zh: ["Tools"],
                  topic_cluster_zh: "工具体系",
                  product_opportunities_zh: [],
                  business_opportunities_zh: [],
                },
              },
            ],
          });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("Annotated Source Alpha");
    expect(screen.getByText("Unnoted Source Beta")).toBeTruthy();

    const notedFilterBtn = screen.getByRole("button", { name: /^有笔记$|^Noted$/i });
    await user.click(notedFilterBtn);

    expect(screen.getByText("Annotated Source Alpha")).toBeTruthy();
    expect(screen.queryByText("Unnoted Source Beta")).toBeNull();
  });

  it("exports and imports personal notes JSON in Settings with conflict-free merge and invalid JSON protection", async () => {
    savePersonalNote("vidExisting", {
      text: "Local note before restore",
      tags: ["旧笔记"],
    });

    const createObjectUrlMock = vi.fn(() => "blob:mock-personal-notes");
    const revokeObjectUrlMock = vi.fn();
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: createObjectUrlMock,
      revokeObjectURL: revokeObjectUrlMock,
    });
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );

    expect(screen.getByText("个人笔记与标签（本机 1 条）")).toBeTruthy();

    await user.click(screen.getByRole("button", { name: /导出个人笔记/i }));
    expect(createObjectUrlMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText("已导出本机个人笔记与标签（共 1 条）。")).toBeTruthy();
    clickSpy.mockRestore();

    const fileInput = screen.getByLabelText("选择个人笔记 JSON 文件") as HTMLInputElement;
    const validFile = new File(
      [
        JSON.stringify({
          version: 1,
          notes: {
            vidImported2: {
              text: "Imported insight",
              tags: ["新导入", "核心"],
              updatedAt: "2026-11-27T09:50:00Z",
            },
          },
        }),
      ],
      "backup.json",
      { type: "application/json" },
    );
    Object.defineProperty(validFile, "text", {
      value: async () =>
        JSON.stringify({
          version: 1,
          notes: {
            vidImported2: {
              text: "Imported insight",
              tags: ["新导入", "核心"],
              updatedAt: "2026-11-27T09:50:00Z",
            },
          },
        }),
    });
    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText("已合并导入 1 条个人笔记，当前本机共 2 条。")).toBeTruthy();
      expect(screen.getByText("个人笔记与标签（本机 2 条）")).toBeTruthy();
    });

    const badFile = new File(["{not-valid-json"], "broken.json", { type: "application/json" });
    Object.defineProperty(badFile, "text", { value: async () => "{not-valid-json" });
    fireEvent.change(fileInput, { target: { files: [badFile] } });

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toContain("未能导入个人笔记");
    });
  });
});
