import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readPersonalNote, savePersonalNote } from "./personalNotes";
import { clearSavedContentViews, readSavedContentViews, saveContentView } from "./savedViews";
import {
  exportStudyWorkspaceSnapshotJson,
  importStudyWorkspaceSnapshotJson,
} from "./studyWorkspaceSnapshot";
import { UiLanguageProvider } from "./uiLanguage";
import { WorkspaceAiSettingsPanel } from "./WorkspaceAiWidgets";

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

describe("Iteration 41 (EVO-W7-06): Unified v2 study state snapshot (notes + tags + saved views JSON)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    vi.stubGlobal("fetch", () => okJson({}));
  });

  afterEach(() => {
    cleanup();
    URL.createObjectURL = origCreateObjectURL;
    URL.revokeObjectURL = origRevokeObjectURL;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("exports v2 snapshot containing notes + saved views, merges v2 cleanly without duplicates, and stays v1-compatible", () => {
    savePersonalNote("v1", { text: "原有个人笔记", tags: ["架构"] });
    saveContentView(
      {
        name: "AI必看视图",
        searchQuery: "",
        providerFilter: "ALL",
        bucketFilter: "MUST_WATCH",
        topicFilter: "AI Agent 工程架构",
        channelFilter: "ALL",
        tagFilter: "ALL",
      },
      true,
    );

    const rawV2 = exportStudyWorkspaceSnapshotJson();
    const parsedV2 = JSON.parse(rawV2) as {
      version: number;
      note_count: number;
      saved_view_count: number;
      notes: Record<string, unknown>;
      saved_views: unknown[];
    };
    expect(parsedV2.version).toBe(2);
    expect(parsedV2.note_count).toBe(1);
    expect(parsedV2.saved_view_count).toBe(1);
    expect(parsedV2.saved_views).toHaveLength(1);

    // Clear and restore from v2
    localStorage.clear();
    clearSavedContentViews();
    const restoreV2 = importStudyWorkspaceSnapshotJson(rawV2);
    expect(restoreV2.importedNotes).toBe(1);
    expect(restoreV2.totalNotes).toBe(1);
    expect(restoreV2.importedViews).toBe(1);
    expect(restoreV2.totalViews).toBe(1);
    expect(readPersonalNote("v1")?.text).toBe("原有个人笔记");
    expect(readSavedContentViews()[0]?.name).toBe("AI必看视图");

    // Re-importing identical v2 deduplicates views cleanly
    const dedupeRes = importStudyWorkspaceSnapshotJson(rawV2);
    expect(dedupeRes.importedViews).toBe(0);
    expect(dedupeRes.totalViews).toBe(1);

    // Backward-compatible with v1 notes-only JSON
    const v1Json = JSON.stringify({
      version: 1,
      notes: {
        v2: {
          text: "V1 导入笔记",
          tags: ["历史恢复"],
          updatedAt: "2026-11-27T09:00:00Z",
        },
      },
    });
    const v1Res = importStudyWorkspaceSnapshotJson(v1Json);
    expect(v1Res.importedNotes).toBe(1);
    expect(v1Res.totalNotes).toBe(2);
    expect(v1Res.importedViews).toBe(0);
    expect(v1Res.totalViews).toBe(1);
  });

  it("exports and merges both personal notes and saved views in Settings backup UI", async () => {
    savePersonalNote("vidSettings1", { text: "笔记内容", tags: ["核心"] });
    saveContentView(
      {
        name: "实战视图",
        searchQuery: "Agent",
        providerFilter: "ALL",
        bucketFilter: "ALL",
        topicFilter: "ALL",
        channelFilter: "ALL",
        tagFilter: "ALL",
      },
      true,
    );

    const blobs: Blob[] = [];
    URL.createObjectURL = vi.fn((blob: Blob | MediaSource) => {
      blobs.push(blob as Blob);
      return "blob:study-v2";
    });
    URL.revokeObjectURL = vi.fn();

    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "导出个人笔记 (.json)" }));
    await waitFor(() => {
      expect(
        screen.getByText("已导出本机个人笔记与标签（共 1 条 · 含 1 个常用视图）。"),
      ).toBeTruthy();
    });

    const v2Payload = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result ?? ""));
      reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
      reader.readAsText(blobs[blobs.length - 1]);
    });
    expect(JSON.parse(v2Payload).version).toBe(2);
    expect(JSON.parse(v2Payload).saved_views).toHaveLength(1);

    const incomingV2 = JSON.stringify({
      version: 2,
      notes: {
        vidSettings2: {
          text: "新设备恢复的思考",
          tags: ["迁移"],
          updatedAt: "2026-11-27T11:00:00Z",
        },
      },
      saved_views: [
        {
          id: "view-import-2",
          name: "恢复视图",
          searchQuery: "",
          providerFilter: "LOCAL",
          bucketFilter: "NOTED",
          topicFilter: "ALL",
          channelFilter: "ALL",
          tagFilter: "ALL",
          createdAt: "2026-11-27T11:00:00Z",
        },
      ],
    });

    const input = screen.getByLabelText("选择个人笔记 JSON 文件") as HTMLInputElement;
    const file = new File([incomingV2], "snapshot-v2.json", { type: "application/json" });
    Object.defineProperty(file, "text", { value: async () => incomingV2 });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(
        screen.getByText(
          "已合并导入 1 条个人笔记与 1 个常用视图，当前本机共 2 条笔记 · 2 个视图。",
        ),
      ).toBeTruthy();
    });
    expect(readSavedContentViews()).toHaveLength(2);
  });
});
