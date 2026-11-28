import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { savePersonalNote } from "./personalNotes";
import { saveContentView } from "./savedViews";

function jsonResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

describe("Iteration 43 — Cmd+K saved smart views & local study power actions", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    localStorage.setItem("yia.onboarding_completed.v1", "1");
    window.location.hash = "#Home";
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    localStorage.clear();
    window.location.hash = "";
  });

  it("exposes saved smart views in Cmd+K and applies all saved filter criteria in Content", async () => {
    savePersonalNote("vidViewMatch", {
      text: "Important architectural boundary insight",
      tags: ["架构实战"],
    });
    saveContentView({
      name: "必看架构批注",
      searchQuery: "Sandbox",
      providerFilter: "ALL",
      bucketFilter: "STARRED",
      topicFilter: "ALL",
      channelFilter: "ALL",
      tagFilter: "架构实战",
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/system") {
          return jsonResponse({ health: "ready", edition: "LOCAL" });
        }
        if (path === "/api/v1/dashboard") {
          return jsonResponse({
            intelligence: [],
            saved_intelligence_ids: [],
            pinned_topics: [],
            needs_attention: [],
          });
        }
        if (path.startsWith("/api/v1/videos")) {
          return jsonResponse({
            videos: [
              {
                video_id: "vidViewMatch",
                title: "Sandbox Boundary Deep Dive",
                provider: "YOUTUBE",
                channel_name: "Atlas",
                processing_status: "SUMMARIZED",
                duration_seconds: 900,
                ai_brief: {
                  score: 9.0,
                  starred: true,
                  is_read: false,
                  headline_zh: "Sandbox 边界清晰拆解",
                  topic_cluster_zh: "Agent",
                },
              },
              {
                video_id: "vidOther",
                title: "Unrelated Video",
                provider: "YOUTUBE",
                channel_name: "Beta",
                processing_status: "SUMMARIZED",
                duration_seconds: 600,
                ai_brief: {
                  score: 7.0,
                  starred: false,
                  is_read: false,
                  headline_zh: "无关内容",
                },
              },
            ],
          });
        }
        if (path === "/api/v1/topics") {
          return jsonResponse({ topics: [] });
        }
        if (path === "/api/v1/intelligence") {
          return jsonResponse({ intelligence: [] });
        }
        if (path === "/api/v1/workspace-ai/research/sessions") {
          return jsonResponse({ sessions: [] });
        }
        return jsonResponse({});
      }),
    );

    const user = userEvent.setup();
    render(<App />);

    const cmdBtn = await screen.findByRole("button", { name: /搜索与直达/ });
    await user.click(cmdBtn);

    const combobox = await screen.findByRole("combobox");
    await user.type(combobox, "必看架构批注");

    const viewOption = await screen.findByText("打开保存视图：必看架构批注");
    await user.click(viewOption);

    expect(window.location.hash).toBe("#Content");
    const searchBox = await screen.findByRole("searchbox");
    expect((searchBox as HTMLInputElement).value).toBe("Sandbox");
    expect(await screen.findByText("Sandbox 边界清晰拆解")).toBeTruthy();
    expect(screen.queryByText("无关内容")).toBeNull();
  });

  it("provides instant local study snapshot export and tag governance navigation in Cmd+K", async () => {
    savePersonalNote("vidSnap1", { text: "Keep this snapshot", tags: ["复盘"] });

    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => {
        if (path === "/api/v1/system") {
          return jsonResponse({ health: "ready", edition: "LOCAL" });
        }
        if (path === "/api/v1/dashboard") {
          return jsonResponse({
            intelligence: [],
            saved_intelligence_ids: [],
            pinned_topics: [],
            needs_attention: [],
          });
        }
        if (path.startsWith("/api/v1/topics")) {
          return jsonResponse({ topics: [] });
        }
        return jsonResponse({ videos: [], intelligence: [], sessions: [] });
      }),
    );

    const origCreateObjectUrl = URL.createObjectURL;
    const origRevokeObjectUrl = URL.revokeObjectURL;
    const createObjectUrlMock = vi.fn(() => "blob:study-snapshot");
    const revokeObjectUrlMock = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: createObjectUrlMock,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: revokeObjectUrlMock,
    });
    const anchorClickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    try {
      const user = userEvent.setup();
      render(<App />);

      const cmdBtn = await screen.findByRole("button", { name: /搜索与直达/ });
      await user.click(cmdBtn);

      const combobox = await screen.findByRole("combobox");
      await user.type(combobox, "备份学习状态");
      await user.click(await screen.findByText("备份学习状态镜像 (.json)"));
      expect(createObjectUrlMock).toHaveBeenCalledTimes(1);
      expect(anchorClickSpy).toHaveBeenCalledTimes(1);

      await user.click(await screen.findByRole("button", { name: /搜索与直达/ }));
      const combobox2 = await screen.findByRole("combobox");
      await user.type(combobox2, "整理自建标签");
      await user.click(await screen.findByText("整理自建标签（重命名 / 合并）"));
      expect(window.location.hash).toBe("#Topics");
    } finally {
      anchorClickSpy.mockRestore();
      Object.defineProperty(URL, "createObjectURL", {
        configurable: true,
        writable: true,
        value: origCreateObjectUrl,
      });
      Object.defineProperty(URL, "revokeObjectURL", {
        configurable: true,
        writable: true,
        value: origRevokeObjectUrl,
      });
    }
  });
});
