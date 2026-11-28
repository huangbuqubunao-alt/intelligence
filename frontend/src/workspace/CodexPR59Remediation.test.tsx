import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { KeyboardShortcutsModal } from "./KeyboardShortcutsModal";
import {
  PERSONAL_NOTES_STORAGE_KEY,
  readPersonalNote,
  renamePersonalTag,
  savePersonalNote,
} from "./personalNotes";
import { ReaderPersonalNoteCard } from "./ReaderPersonalNoteCard";
import {
  buildResearchDossierMarkdown,
  buildResearchSynthesisMarkdown,
  classifyResearchSessionTrust,
} from "./researchExport";
import { clearSavedContentViews, saveContentView } from "./savedViews";
import {
  exportStudyWorkspaceSnapshotJson,
  exportStudyWorkspaceSnapshotParts,
  importStudyWorkspaceSnapshotJson,
} from "./studyWorkspaceSnapshot";
import { UiLanguageProvider } from "./uiLanguage";
import {
  type AiResearchSession,
  formatPlainTextResearchBrief,
  WeeklyAiBriefPanel,
  WorkspaceAiResearchPanel,
  WorkspaceAiSettingsPanel,
} from "./WorkspaceAiWidgets";

function okJson(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

describe("Codex PR #59 Remediation (P1-01..P1-04, P2-01..P2-09, P3-01)", () => {
  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("P1-01 & P2-02: syncs cross-tab edits cleanly, never overwrites on untouched blur, protects concurrent drafts, and flushes on quick unmount", async () => {
    savePersonalNote("vidTab", { text: "Note A", tags: ["初始"] });

    render(
      <UiLanguageProvider>
        <div>
          <ReaderPersonalNoteCard videoId="vidTab" />
          <ReaderPersonalNoteCard videoId="vidTab" />
        </div>
      </UiLanguageProvider>,
    );

    const textareas = screen.getAllByLabelText("我的思考与批注内容") as HTMLTextAreaElement[];
    expect(textareas[0].value).toBe("Note A");
    expect(textareas[1].value).toBe("Note A");

    // Tab 1 writes and blurs -> Note B saved
    fireEvent.change(textareas[0], { target: { value: "Note B" } });
    fireEvent.blur(textareas[0]);
    expect(readPersonalNote("vidTab")?.text).toBe("Note B");

    // Simulate Tab 2 receiving Chrome cross-tab storage event
    fireEvent(
      window,
      new StorageEvent("storage", { key: PERSONAL_NOTES_STORAGE_KEY }),
    );
    expect(textareas[1].value).toBe("Note B");

    // Untouched focus + blur on Tab 2 must perform zero overwrite
    fireEvent.focus(textareas[1]);
    fireEvent.blur(textareas[1]);
    expect(readPersonalNote("vidTab")?.text).toBe("Note B");

    // Concurrent dirty draft on Tab 2 vs external save -> conflict banner instead of silent overwrite
    fireEvent.change(textareas[1], { target: { value: "Tab2 Concurrent Draft" } });
    expect(screen.getByText("正在保存…")).toBeTruthy();

    savePersonalNote("vidTab", { text: "Tab1 Remote Edit", tags: ["远端标签"] });
    fireEvent(
      window,
      new StorageEvent("storage", { key: PERSONAL_NOTES_STORAGE_KEY }),
    );
    expect(screen.getByRole("alert").textContent).toContain("检测到其他标签页已更新此笔记");

    fireEvent.blur(textareas[1]);
    expect(readPersonalNote("vidTab")?.text).toBe("Tab1 Remote Edit");

    fireEvent.click(screen.getByRole("button", { name: "合并并保留两边" }));
    const merged = readPersonalNote("vidTab");
    expect(merged?.text).toContain("Tab1 Remote Edit");
    expect(merged?.text).toContain("Tab2 Concurrent Draft");
    expect(merged?.tags).toContain("远端标签");

    // P2-02: Unmount inside 280ms debounce window flushes draft synchronously
    cleanup();
    localStorage.clear();
    const { unmount } = render(
      <UiLanguageProvider>
        <ReaderPersonalNoteCard videoId="vidQuickNav" />
      </UiLanguageProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: "写笔记" }));
    const quickBox = screen.getByLabelText("我的思考与批注内容");
    fireEvent.change(quickBox, { target: { value: "Fast typed before unmount" } });
    expect(screen.getByText("正在保存…")).toBeTruthy();
    unmount();
    expect(readPersonalNote("vidQuickNav")?.text).toBe("Fast typed before unmount");
  });

  it("P1-02 & P1-03: round-trips 501-note v2 snapshots cleanly and blocks undated/malformed/equal-ts v1 overwrites", () => {
    for (let i = 1; i <= 501; i += 1) {
      savePersonalNote(`vid_${i}`, {
        text: `Short note #${i}`,
        tags: [i % 2 === 0 ? "偶数" : "奇数"],
      });
    }
    saveContentView({
      name: "501视图",
      searchQuery: "",
      providerFilter: "ALL",
      bucketFilter: "STARRED",
      topicFilter: "ALL",
      channelFilter: "ALL",
      tagFilter: "ALL",
    });

    const raw501 = exportStudyWorkspaceSnapshotJson();
    expect(raw501.length).toBeGreaterThan(40000);

    localStorage.clear();
    clearSavedContentViews();

    const restored = importStudyWorkspaceSnapshotJson(raw501);
    expect(restored.notesPersisted).toBe(true);
    expect(restored.importedNotes).toBe(501);
    expect(restored.totalNotes).toBe(501);
    expect(restored.importedViews).toBe(1);
    expect(readPersonalNote("vid_501")?.text).toBe("Short note #501");

    // P1-03: undated / malformed / identical-ts different-content v1 notes never overwrite newer local record
    localStorage.clear();
    localStorage.setItem(
      PERSONAL_NOTES_STORAGE_KEY,
      JSON.stringify({
        vidConflict: {
          text: "Current Newer Note",
          tags: ["核心", "本地"],
          updatedAt: "2026-11-27T12:00:00Z",
        },
      }),
    );

    const undatedV1 = JSON.stringify({
      version: 1,
      notes: {
        vidConflict: { text: "Old Undated Text", tags: [] },
        vidBrandNewUndated: { text: "Fresh undated import", tags: ["历史"] },
      },
    });
    const rUndated = importStudyWorkspaceSnapshotJson(undatedV1);
    expect(rUndated.noteConflicts).toBe(1);
    expect(readPersonalNote("vidConflict")?.text).toBe("Current Newer Note");
    expect(readPersonalNote("vidConflict")?.tags).toEqual(["核心", "本地"]);
    expect(readPersonalNote("vidBrandNewUndated")?.updatedAt).toBe(new Date(0).toISOString());

    const malformedV1 = JSON.stringify({
      version: 1,
      notes: {
        vidConflict: { text: "Broken TS", tags: [], updatedAt: "not-a-timestamp" },
      },
    });
    expect(importStudyWorkspaceSnapshotJson(malformedV1).noteConflicts).toBe(1);
    expect(readPersonalNote("vidConflict")?.text).toBe("Current Newer Note");

    const equalTsDiffV1 = JSON.stringify({
      version: 1,
      notes: {
        vidConflict: {
          text: "Different Text Same TS",
          tags: [],
          updatedAt: "2026-11-27T12:00:00Z",
        },
      },
    });
    expect(importStudyWorkspaceSnapshotJson(equalTsDiffV1).noteConflicts).toBe(1);
    expect(readPersonalNote("vidConflict")?.text).toBe("Current Newer Note");

    // Round 2 P1-03 counterexamples:
    // 1) All 6 permutations of (Jan 1 A, Mar 1 A, Feb 1 B) converge to Mar 1 A with tags intact
    const janA = JSON.stringify({
      version: 1,
      notes: { vidPerm: { text: "A", tags: ["core"], updatedAt: "2026-01-01T00:00:00Z" } },
    });
    const marA = JSON.stringify({
      version: 1,
      notes: { vidPerm: { text: "A", tags: ["core"], updatedAt: "2026-03-01T00:00:00Z" } },
    });
    const febB = JSON.stringify({
      version: 1,
      notes: { vidPerm: { text: "B", tags: ["core"], updatedAt: "2026-02-01T00:00:00Z" } },
    });
    const permutations = [
      [janA, marA, febB],
      [janA, febB, marA],
      [marA, janA, febB],
      [marA, febB, janA],
      [febB, janA, marA],
      [febB, marA, janA],
    ];
    for (const order of permutations) {
      localStorage.clear();
      for (const snap of order) {
        importStudyWorkspaceSnapshotJson(snap);
      }
      const settled = readPersonalNote("vidPerm");
      expect(settled?.text).toBe("A");
      expect(settled?.tags).toEqual(["core"]);
      expect(settled?.updatedAt).toBe("2026-03-01T00:00:00Z");
    }

    // 2) Invalid Gregorian calendar dates (2030-02-30, 2026-02-29 non-leap, 2026-04-31) never overwrite
    localStorage.clear();
    importStudyWorkspaceSnapshotJson(janA);
    for (const badIso of [
      "2030-02-30T00:00:00Z",
      "2026-02-29T00:00:00Z",
      "2026-04-31T00:00:00Z",
    ]) {
      const badDateSnap = JSON.stringify({
        version: 1,
        notes: { vidPerm: { text: "Corrupted Bad Date", tags: [], updatedAt: badIso } },
      });
      const resBad = importStudyWorkspaceSnapshotJson(badDateSnap);
      expect(resBad.noteConflicts).toBe(1);
      expect(readPersonalNote("vidPerm")?.text).toBe("A");
    }
    // Valid leap-year date (2028-02-29) is accepted cleanly
    const leapValidSnap = JSON.stringify({
      version: 1,
      notes: { vidPerm: { text: "Leap Updated", tags: ["leap"], updatedAt: "2028-02-29T00:00:00Z" } },
    });
    expect(importStudyWorkspaceSnapshotJson(leapValidSnap).importedNotes).toBe(1);
    expect(readPersonalNote("vidPerm")?.text).toBe("Leap Updated");
  });

  it("P1-02 multi-volume sharding: splits 10,001 notes and two 5.4 MiB UTF-8 Chinese notes cleanly and round-trips 100% without truncation", () => {
    // 1) Sequential 6,000 + 4,000 + 1 import -> 10,001 notes in store
    const makeBatch = (start: number, count: number) => {
      const notes: Record<string, { text: string; tags: string[]; updatedAt: string }> = {};
      for (let i = start; i < start + count; i += 1) {
        notes[`n_${i}`] = {
          text: `Short #${i}`,
          tags: ["b"],
          updatedAt: "2026-11-27T08:00:00Z",
        };
      }
      return JSON.stringify({ version: 2, notes });
    };
    expect(importStudyWorkspaceSnapshotJson(makeBatch(1, 6000)).totalNotes).toBe(6000);
    expect(importStudyWorkspaceSnapshotJson(makeBatch(6001, 4000)).totalNotes).toBe(10000);
    expect(importStudyWorkspaceSnapshotJson(makeBatch(10001, 1)).totalNotes).toBe(10001);
    saveContentView({
      name: "万条视图",
      searchQuery: "",
      providerFilter: "ALL",
      bucketFilter: "NOTED",
      topicFilter: "ALL",
      channelFilter: "ALL",
      tagFilter: "ALL",
    });

    const parts10001 = exportStudyWorkspaceSnapshotParts();
    expect(parts10001).toHaveLength(2);
    expect(parts10001[0].noteCount).toBe(10000);
    expect(parts10001[1].noteCount).toBe(1);
    expect(parts10001[0].byteLength).toBeLessThanOrEqual(10 * 1024 * 1024);
    expect(parts10001[1].byteLength).toBeLessThanOrEqual(10 * 1024 * 1024);

    localStorage.clear();
    clearSavedContentViews();
    for (const part of parts10001) {
      importStudyWorkspaceSnapshotJson(part.json);
    }
    expect(readPersonalNote("n_1")?.text).toBe("Short #1");
    expect(readPersonalNote("n_10001")?.text).toBe("Short #10001");

    // 2) Two long Chinese notes whose combined UTF-8 JSON exceeds 10 MiB (> 5.4 MB UTF-8 each)
    localStorage.clear();
    clearSavedContentViews();
    const chinese1800k = "测".repeat(1800000); // ~5.4 MB UTF-8 for only 1.8M JS UTF-16 chars!
    const f1 = JSON.stringify({
      version: 2,
      notes: { zh_1: { text: chinese1800k, tags: ["中文"], updatedAt: "2026-11-27T08:00:00Z" } },
    });
    const f2 = JSON.stringify({
      version: 2,
      notes: { zh_2: { text: chinese1800k, tags: ["中文"], updatedAt: "2026-11-27T09:00:00Z" } },
    });
    expect(importStudyWorkspaceSnapshotJson(f1).totalNotes).toBe(1);
    expect(importStudyWorkspaceSnapshotJson(f2).totalNotes).toBe(2);

    const zhParts = exportStudyWorkspaceSnapshotParts();
    expect(zhParts).toHaveLength(2);
    expect(zhParts[0].byteLength).toBeLessThanOrEqual(10 * 1024 * 1024);
    expect(zhParts[1].byteLength).toBeLessThanOrEqual(10 * 1024 * 1024);

    localStorage.clear();
    for (const part of zhParts) {
      importStudyWorkspaceSnapshotJson(part.json);
    }
    expect(readPersonalNote("zh_1")?.text.length).toBe(1800000);
    expect(readPersonalNote("zh_2")?.text.length).toBe(1800000);
  });

  it("P1-02 quota matrix: Settings backup UI accurately reports notesPersisted=false even when viewsPersisted=true (0 views or 1 view) and notes+views both failing", async () => {
    vi.stubGlobal("fetch", () => okJson({}));
    savePersonalNote("vSeed", { text: "Seed", tags: [] });

    let failNotesWrite = true;
    let failViewsWrite = false;
    const storageProto = Object.getPrototypeOf(window.localStorage) as Storage;
    const origSetItem = storageProto.setItem;
    vi.spyOn(storageProto, "setItem").mockImplementation(function (
      this: Storage,
      key: string,
      value: string,
    ) {
      if (failNotesWrite && key === PERSONAL_NOTES_STORAGE_KEY) {
        throw new Error("QuotaExceededError");
      }
      if (failViewsWrite && key === "yia.content_saved_views.v1") {
        throw new Error("QuotaExceededError");
      }
      return origSetItem.call(this, key, value);
    });

    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );
    const fileInput = screen.getByLabelText("选择个人笔记 JSON 文件") as HTMLInputElement;

    // Case A: notesPersisted=false, viewsPersisted=true (no views in snapshot)
    const notesOnlyPayload = JSON.stringify({
      version: 2,
      notes: { vBig: { text: "Too large for quota", tags: [], updatedAt: "2026-11-27T12:00:00Z" } },
    });
    const fileA = new File([notesOnlyPayload], "notes-only.json", { type: "application/json" });
    Object.defineProperty(fileA, "text", { value: async () => notesOnlyPayload });
    fireEvent.change(fileInput, { target: { files: [fileA] } });
    await waitFor(() => {
      expect(screen.getByText(/未能保存个人笔记：浏览器本地存储空间不足/)).toBeTruthy();
    });
    expect(screen.queryByText(/已合并导入/)).toBeNull();

    // Case B: notesPersisted=false, viewsPersisted=true (1 saved view succeeds)
    const mixedPayload = JSON.stringify({
      version: 2,
      notes: { vBig: { text: "Too large for quota", tags: [], updatedAt: "2026-11-27T12:00:00Z" } },
      saved_views: [
        {
          id: "view-ok",
          name: "小视图",
          searchQuery: "",
          providerFilter: "ALL",
          bucketFilter: "STARRED",
          topicFilter: "ALL",
          channelFilter: "ALL",
          tagFilter: "ALL",
          createdAt: "2026-11-27T12:00:00Z",
        },
      ],
    });
    const fileB = new File([mixedPayload], "mixed.json", { type: "application/json" });
    Object.defineProperty(fileB, "text", { value: async () => mixedPayload });
    fireEvent.change(fileInput, { target: { files: [fileB] } });
    await waitFor(() => {
      expect(
        screen.getByText(/未能保存个人笔记：浏览器本地存储空间不足.*仅合并了 1 个常用视图/),
      ).toBeTruthy();
    });

    // Case C: both notesPersisted=false and viewsPersisted=false (distinct new view triggers view write)
    failViewsWrite = true;
    const bothFailPayload = JSON.stringify({
      version: 2,
      notes: { vBig2: { text: "Too large too", tags: [], updatedAt: "2026-11-27T12:00:00Z" } },
      saved_views: [
        {
          id: "view-fail-both",
          name: "另一个视图",
          searchQuery: "agent",
          providerFilter: "ALL",
          bucketFilter: "NOTED",
          topicFilter: "ALL",
          channelFilter: "ALL",
          tagFilter: "ALL",
          createdAt: "2026-11-27T12:00:00Z",
        },
      ],
    });
    const fileC = new File([bothFailPayload], "both-fail.json", { type: "application/json" });
    Object.defineProperty(fileC, "text", { value: async () => bothFailPayload });
    fireEvent.change(fileInput, { target: { files: [fileC] } });
    await waitFor(() => {
      expect(
        screen.getByText(/未能导入个人笔记与常用视图：浏览器本地存储空间不足/),
      ).toBeTruthy();
    });
  });

  it("P2-01 & P2-04: verifies saved-view quota partial persistence honestly and rejects oversized files before reading", async () => {
    vi.stubGlobal("fetch", () => okJson({}));
    savePersonalNote("vSeed", { text: "Seed", tags: [] });

    const storageProto = Object.getPrototypeOf(window.localStorage) as Storage;
    const origSetItem = storageProto.setItem;
    vi.spyOn(storageProto, "setItem").mockImplementation(function (
      this: Storage,
      key: string,
      value: string,
    ) {
      if (key === "yia.content_saved_views.v1") {
        throw new Error("QuotaExceededError");
      }
      return origSetItem.call(this, key, value);
    });

    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );

    const fileInput = screen.getByLabelText("选择个人笔记 JSON 文件") as HTMLInputElement;
    const payload = JSON.stringify({
      version: 2,
      notes: { vOk: { text: "Persisted note", tags: [], updatedAt: "2026-11-27T12:00:00Z" } },
      saved_views: [
        {
          id: "view-quota-fail",
          name: "配额不足视图",
          searchQuery: "",
          providerFilter: "ALL",
          bucketFilter: "STARRED",
          topicFilter: "ALL",
          channelFilter: "ALL",
          tagFilter: "ALL",
          createdAt: "2026-11-27T12:00:00Z",
        },
      ],
    });
    const okFile = new File([payload], "snap.json", { type: "application/json" });
    Object.defineProperty(okFile, "text", { value: async () => payload });
    fireEvent.change(fileInput, { target: { files: [okFile] } });

    await waitFor(() => {
      expect(
        screen.getByText(/但因存储空间限制未能保存 1 个常用视图/),
      ).toBeTruthy();
    });

    // P2-04: Oversized file is rejected by File.size before file.text() runs
    const textSpy = vi.fn(async () => "{}");
    const bigFile = new File(["{}"], "huge.json", { type: "application/json" });
    Object.defineProperty(bigFile, "size", { value: 11 * 1024 * 1024 });
    Object.defineProperty(bigFile, "text", { value: textSpy });
    fireEvent.change(fileInput, { target: { files: [bigFile] } });

    await waitFor(() => {
      expect(screen.getByText(/超过 10 MiB 限制/)).toBeTruthy();
    });
    expect(textSpy).not.toHaveBeenCalled();
  });

  it("P1-04 & P3-01: preserves Demo PARTIAL_PRUNED_HEURISTIC posture, attributes all cited sources, excludes NEEDS_REVERIFICATION/verified:false, and fixes YAML frontmatter heading hierarchy", async () => {
    const demoHeuristicSession: AiResearchSession = {
      session_id: "sess-demo-heuristic",
      question: "为什么必须确定性审计？",
      answer_status: "GROUNDED",
      source_integrity_status: "VERIFIED",
      fact_verification_state: "PARTIAL_PRUNED_HEURISTIC",
      contains_heuristic_claims: true,
      pinned: true,
      refused: false,
      scope_label_zh: "全库对比",
      answer_zh: "先把字幕锁死再做引用绑定 [E1][E2]。",
      key_takeaways_zh: ["时间轴锁死来源"],
      action_items_zh: [],
      citations: [
        {
          ref_label: "E1",
          video_id: "vidOne",
          video_title: "Deterministic Agents",
          channel_name: "Atlas",
          evidence_id: "ev1",
          start_ms: 18000,
          end_ms: 25000,
          timestamp_label: "00:18",
          excerpt: "Lock transcripts first.",
          verified: true,
        },
        {
          ref_label: "E2",
          video_id: "vidTwo",
          video_title: "Bilibili Evidence Chain",
          channel_name: "Geek",
          evidence_id: "ev2",
          start_ms: 42000,
          end_ms: 50000,
          timestamp_label: "00:42",
          excerpt: "Bind hashes cleanly.",
          verified: true,
        },
      ],
      obsidian_markdown:
        "---\ntitle: 测试笔记\ntags: [agent]\n---\n# 为什么必须确定性审计？\n\n## 核心结论\n内容正文。",
      provider: "demo-replay",
      model: "demo-replay",
      created_at: "2026-11-27T09:00:00Z",
    };

    const staleSession: AiResearchSession = {
      ...demoHeuristicSession,
      session_id: "sess-stale",
      question: "Stale Session",
      answer_status: "NEEDS_REVERIFICATION",
      source_integrity_status: "NEEDS_REVERIFICATION",
      fact_verification_state: "NEEDS_REVERIFICATION",
      contains_heuristic_claims: false,
      pinned: false,
    };

    const falseCitedSession: AiResearchSession = {
      ...demoHeuristicSession,
      session_id: "sess-unverified-cites",
      question: "Unverified Cites",
      fact_verification_state: "SUPPORTED",
      contains_heuristic_claims: false,
      citations: demoHeuristicSession.citations.map((c) => ({ ...c, verified: false })),
    };

    const verifiedSession: AiResearchSession = {
      ...demoHeuristicSession,
      session_id: "sess-verified",
      question: "Verified Question?",
      fact_verification_state: "SUPPORTED",
      source_integrity_status: "VERIFIED",
      contains_heuristic_claims: false,
      pinned: false,
      obsidian_markdown: "# Verified Question?\n\n正文已严格核验。",
    };

    expect(classifyResearchSessionTrust(demoHeuristicSession)).toBe("PARTIAL_OR_HEURISTIC");
    expect(classifyResearchSessionTrust(verifiedSession)).toBe("VERIFIED_EXACT");
    expect(classifyResearchSessionTrust(staleSession)).toBe("NEEDS_REVERIFICATION");
    expect(classifyResearchSessionTrust(falseCitedSession)).toBe("REFUSED");
    expect(buildResearchSynthesisMarkdown(staleSession, true)).toBe("");
    expect(formatPlainTextResearchBrief(staleSession, true)).toBe("");
    expect(formatPlainTextResearchBrief(falseCitedSession, true)).toBe("");

    const heuristicPlainZh = formatPlainTextResearchBrief(demoHeuristicSession, true);
    const heuristicPlainEn = formatPlainTextResearchBrief(demoHeuristicSession, false);
    expect(heuristicPlainZh).toContain("证据等级：部分未支持内容已裁剪 · 含启发式关联（请核对原话）");
    expect(heuristicPlainZh).toContain("原话时间轴出处（请对照核验）：");
    expect(heuristicPlainEn).toContain("Trust posture: Unsupported parts pruned");
    expect(heuristicPlainEn).not.toContain("Verified citations:");

    const verifiedPlainEn = formatPlainTextResearchBrief(verifiedSession, false);
    expect(verifiedPlainEn).toContain("Trust posture: Strictly verified");
    expect(verifiedPlainEn).toContain("Verified citations:");

    const dossier = buildResearchDossierMarkdown(
      [demoHeuristicSession, staleSession, falseCitedSession],
      true,
    );
    expect(dossier.includedCount).toBe(1);
    expect(dossier.verifiedCount).toBe(0);
    expect(dossier.heuristicCount).toBe(1);
    expect(dossier.skippedCount).toBe(2);
    expect(dossier.markdown).not.toContain("Stale Session");
    expect(dossier.markdown).not.toContain("Unverified Cites");
    expect(dossier.markdown).not.toContain("严格已核验问答：1");
    expect(dossier.markdown).toContain("## 1. [置顶] 为什么必须确定性审计？ [含启发式/部分裁剪]");
    expect(dossier.markdown).toContain("### 核心结论");
    expect(dossier.markdown.match(/^# /gm)).toHaveLength(1);
    expect(dossier.markdown).toContain("证据等级：部分未支持内容已裁剪");

    vi.stubGlobal("fetch", (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/v1/workspace-ai/research/sessions")) {
        return okJson({
          sessions: [demoHeuristicSession, staleSession],
          suggested_questions: [],
          scope_options: { starred_count: 0, channels: [], topic_clusters: [], videos: [] },
        });
      }
      return okJson({});
    });

    render(
      <UiLanguageProvider>
        <WorkspaceAiResearchPanel onOpen={vi.fn()} />
      </UiLanguageProvider>,
    );

    const saveBtn = await screen.findByRole("button", {
      name: "摘录进来源批注（含启发式提示）",
    });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/已将跨来源研究结论（综合 2 篇出处 · 含启发式提示）/),
      ).toBeTruthy();
    });
    const note = readPersonalNote("vidOne");
    expect(note?.text).toContain("Deterministic Agents");
    expect(note?.text).toContain("Bilibili Evidence Chain");
    expect(note?.text).toContain("部分未支持内容已裁剪");

    // Heuristic session single-item copy/download carry trust posture notice
    const copiedTexts: string[] = [];
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn(async (text: string) => {
          copiedTexts.push(text);
        }),
      },
    });
    const downloadedBlobs: Blob[] = [];
    const origCreateObjectUrl = URL.createObjectURL;
    const origRevokeObjectUrl = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn((blob: Blob | MediaSource) => {
      downloadedBlobs.push(blob as Blob);
      return "blob:research-single";
    });
    URL.revokeObjectURL = vi.fn();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    try {
      fireEvent.click(screen.getByRole("button", { name: "复制纯文本提纲" }));
      fireEvent.click(screen.getByRole("button", { name: "复制双链问答" }));
      fireEvent.click(screen.getByRole("button", { name: "下载 .md" }));
      await waitFor(() => expect(copiedTexts).toHaveLength(2));
      expect(copiedTexts[0]).toContain("证据等级：部分未支持内容已裁剪");
      expect(copiedTexts[1]).toContain("证据等级：部分未支持内容已裁剪");
      expect(downloadedBlobs).toHaveLength(1);
      const mdText = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result ?? ""));
        reader.onerror = () => reject(reader.error ?? new Error("FileReader error"));
        reader.readAsText(downloadedBlobs[0]);
      });
      expect(mdText).toContain("证据等级：部分未支持内容已裁剪");
      expect(clickSpy).toHaveBeenCalled();
    } finally {
      URL.createObjectURL = origCreateObjectUrl;
      URL.revokeObjectURL = origRevokeObjectUrl;
    }

    // Switching to NEEDS_REVERIFICATION session blocks ALL 5 single-session export & save exits
    fireEvent.click(screen.getByRole("button", { name: /Stale Session/ }));
    expect(screen.queryByRole("button", { name: "复制纯文本提纲" })).toBeNull();
    expect(screen.queryByRole("button", { name: "复制双链问答" })).toBeNull();
    expect(screen.queryByRole("button", { name: "下载 .md" })).toBeNull();
    expect(screen.queryByRole("button", { name: /沉淀为本地研究笔记/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /摘录进来源批注/ })).toBeNull();
    expect(screen.getByText(/已暂停复制、下载与入库/)).toBeTruthy();
  });

  it("P2-05, P2-06 & P2-09: blocks multi-word tag truncation, traps Tab focus inside KeyboardShortcutsModal, and starts WeeklyAiBriefPanel compact", async () => {
    savePersonalNote("vTag", { text: "Body", tags: ["old"] });
    const badRename = renamePersonalTag("old", "new tag");
    expect(badRename.error).toBe("MULTI_TOKEN");
    expect(readPersonalNote("vTag")?.tags).toEqual(["old"]);

    const user = userEvent.setup();
    render(
      <UiLanguageProvider>
        <>
          <button type="button">Outside Background Button</button>
          <KeyboardShortcutsModal
            open
            onClose={vi.fn()}
            onOpenCommandPalette={vi.fn()}
          />
        </>
      </UiLanguageProvider>,
    );

    const closeBtn = screen.getByRole("button", { name: "关闭快捷键指南" });
    const paletteBtn = screen.getByRole("button", { name: "打开 ⌘K 命令面板" });
    closeBtn.focus();
    expect(document.activeElement).toBe(closeBtn);
    await user.tab();
    expect(document.activeElement).toBe(paletteBtn);
    await user.tab();
    expect(document.activeElement).toBe(closeBtn);
    await user.tab({ shift: true });
    expect(document.activeElement).toBe(paletteBtn);

    cleanup();
    render(
      <UiLanguageProvider>
        <WeeklyAiBriefPanel
          initialBrief={{
            brief_id: "wk-1",
            title_zh: "本周工程简报",
            week_label: "11/20-11/27",
            funnel_stats: {
              total_videos: 6,
              shorts_filtered_count: 1,
              must_watch_count: 5,
            },
            executive_summary_zh: "一句话高信号摘要。",
            core_trends_zh: ["趋势一"],
            product_opportunities_zh: ["启发一"],
            business_opportunities_zh: ["切口一"],
            must_watch_picks: [
              {
                video_id: "v1",
                title: "精选长视频一",
                channel_name: "Atlas",
                score: 9.2,
                reason_zh: "原因",
              },
            ],
            obsidian_markdown: "# Weekly",
            provider: "demo-replay",
            model: "demo-replay",
            created_at: "2026-11-27T08:00:00Z",
          }}
          onOpenContent={vi.fn()}
          onOpenResearch={vi.fn()}
        />
      </UiLanguageProvider>,
    );

    expect(screen.getByText("一句话高信号摘要。")).toBeTruthy();
    expect(screen.queryByText("精选长视频一")).toBeNull();
    const expandBtn = screen.getByRole("button", { name: /展开完整周报详情/ });
    expect(expandBtn.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(expandBtn);
    expect(screen.getByText("精选长视频一")).toBeTruthy();
  });
});
