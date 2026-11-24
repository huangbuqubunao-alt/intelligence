import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import {
  VideoVisualAnalysis,
  WorkspaceAiSettingsPanel,
  WorkspaceVisualKeyframePanel,
  setPendingResearchVideoIds,
} from "./WorkspaceAiWidgets";
import { UiLanguageProvider } from "./uiLanguage";

function okJson(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => body,
  } as Response);
}

function makeVideoItem(idx: number, overrides: Record<string, unknown> = {}) {
  const id = `vid-${String(idx).padStart(3, "0")}`;
  return {
    video_id: id,
    provider: "YOUTUBE",
    channel_id: "ch-main",
    channel_name: "Scale Lab",
    title: `Library Video ${idx}`,
    published_at: "2026-11-23T10:00:00Z",
    processing_status: "ORGANIZED",
    last_updated: "2026-11-23T10:00:00Z",
    duration_seconds: 900,
    note: { status: "UNAVAILABLE", reason_code: "NOT_GENERATED" },
    scoring: { status: "UNAVAILABLE" },
    ai_brief: {
      headline_zh: `核心结论 ${idx}`,
      summary_zh: `详细摘要 ${idx}`,
      score: 8.5,
      recommendation_tier: "MUST_WATCH",
      content_bucket: "DEEP_DIVE",
      is_short_noise: false,
      starred: idx === 1,
      is_read: false,
      topic_cluster_zh: idx === 1 ? "旧专题Alpha" : "新专题Beta",
    },
    ...overrides,
  };
}

function makeVisualAnalysis(): VideoVisualAnalysis {
  return {
    video_id: "vid-kf-1",
    visual_summary_zh: "架构图与耗时统计汇总",
    visual_takeaways_zh: ["仅抽关键帧并支持离线备份"],
    frame_count: 2,
    informative_frame_count: 2,
    provider: "local_ollama",
    model: "gemma3:4b",
    updated_at: "2026-11-23T15:00:00Z",
    frames: [
      {
        frame_index: 1,
        frame_id: "kf_001",
        filename: "kf_001.jpg",
        timestamp_ms: 1000,
        timestamp_label: "00:01",
        selection_reason: "SCENE",
        frame_kind: "ARCHITECTURE",
        has_visual_info: true,
        title_zh: "三层系统架构图",
        visual_detail_zh: "展示本地优先调度与读写隔离。",
        transcript_fusion_zh: "对应开篇讲解。",
        nearby_transcript: "先看三层系统架构图。",
        image_url: "/api/v1/workspace-ai/videos/vid-kf-1/keyframes/kf_001.jpg",
        image_available: true,
      },
      {
        frame_index: 2,
        frame_id: "kf_002",
        filename: "kf_002.jpg",
        timestamp_ms: 5000,
        timestamp_label: "00:05",
        selection_reason: "SCENE",
        frame_kind: "CHART",
        has_visual_info: true,
        title_zh: "列表冷读延迟对比",
        visual_detail_zh: "展示分页只查当页摘要的收益。",
        transcript_fusion_zh: "避免拉全库 Markdown。",
        nearby_transcript: "列表只需读取本页关键字段。",
        image_url: "/api/v1/workspace-ai/videos/vid-kf-1/keyframes/kf_002.jpg",
        image_available: true,
      },
    ],
  };
}

function baseHandlers(input: string, extra?: (path: string) => Promise<Response> | null) {
  if (extra) {
    const hit = extra(input);
    if (hit) return hit;
  }
  if (input.endsWith("/system")) {
    return okJson({
      release_posture: "PUBLIC_BETA",
      deep_analysis_tier: "EXPERIMENTAL",
      capabilities: {},
    });
  }
  if (input.endsWith("/dashboard")) {
    return okJson({
      counts: { videos: 2, organized: 2, sources: 1, intelligence: 1 },
      needs_attention: [],
      intelligence: [],
      pinned_topics: [],
      workspace_sync_status: { total_videos: 2, briefed_count: 2, pending_count: 0 },
    });
  }
  if (input.endsWith("/workspace-ai/settings")) {
    return okJson({
      active_mode: "local_ollama",
      ollama_base_url: "http://127.0.0.1:11434",
      ollama_model: "qwen3.5:9b",
      cloud_provider: "deepseek",
      cloud_base_url: "https://api.deepseek.com/v1",
      cloud_model: "deepseek-chat",
      cloud_key_configured: false,
      cloud_daily_call_limit: 5,
      cloud_calls_today: 0,
    });
  }
  if (input.endsWith("/intelligence")) return okJson({ intelligence: [], activity: [] });
  if (input.endsWith("/research")) return okJson({ research: [], total: 0 });
  if (input.endsWith("/settings/source-policy")) {
    return okJson({
      policy: {
        initial_history_count: 5,
        per_run_max_new_videos: 5,
        focus_rules: [],
        ignore_rules: [],
        distillation_style: "BALANCED",
      },
    });
  }
  if (input.endsWith("/settings/resource-usage")) return okJson({ usage: [] });
  if (input.endsWith("/settings")) {
    return okJson({
      general: {
        timezone: "Asia/Shanghai",
        output_language: "zh-CN",
        output_language_source: "BOOTSTRAP_DEFAULT",
        output_language_updated_at: null,
      },
      providers: [],
    });
  }
  if (input.endsWith("/preferences")) return okJson({ active: null, history: [] });
  if (input.endsWith("/settings/cloud-spending-policy")) {
    return okJson({
      spending_policy: {
        enabled: false,
        revision: 1,
        total_cny: 0,
        per_request_cny: 0,
        max_calls: 0,
      },
    });
  }
  if (input.endsWith("/topics")) return okJson({ topics: [] });
  if (input.endsWith("/sources")) return okJson({ sources: [] });
  if (input.endsWith("/saved-intelligence")) return okJson({ saved: [] });
  if (input.endsWith("/creator-following/capability")) return okJson({ supported: false });
  if (input.endsWith("/local/transcription/capability")) {
    return okJson({ state: "READY", available: true });
  }
  if (input.endsWith("/workspace-ai/weekly-brief")) return okJson({ weekly_brief: null });
  if (input.endsWith("/workspace-ai/research/sessions")) {
    return okJson({
      sessions: [],
      suggested_questions: [],
      scope_options: { channels: [], topic_clusters: [], starred_count: 0, videos: [] },
    });
  }
  return okJson({});
}

describe("Codex Review Remediation Frontend Regression Suite", () => {
  beforeEach(() => {
    localStorage.setItem("yia.ui-language", "zh-CN");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    localStorage.clear();
    location.hash = "";
  });

  it("P1-06: deep-linking to tail evidence_id fetches segment #31 and displays explicit warning on stale evidence", async () => {
    const base21 = Array.from({ length: 21 }, (_, idx) => ({
      evidence_id: `ev-${idx + 1}`,
      artifact_id: "art-1",
      locator_type: "TIME_RANGE",
      start_line: null,
      end_line: null,
      start_ms: idx * 2000,
      end_ms: (idx + 1) * 2000,
      source_language: "zh",
      language: "zh",
      original_excerpt: `第 ${idx + 1} 段基准原文。`,
      lineage_kind: "ORIGINAL_TRANSCRIPT",
      role: "PRIMARY_ORIGINAL",
      translated_excerpt: null,
      translated_language: null,
      translation_target_language: "zh-CN",
      source_url: null,
    }));
    const tail31 = {
      ...base21[0],
      evidence_id: "ev-31",
      start_ms: 60000,
      end_ms: 62000,
      original_excerpt: "尾段三十一关键依据",
    };
    const tailVideo = makeVideoItem(1, { video_id: "vid-tail", title: "Long Tail Video" });
    const fetchMock = vi.fn((input: string) =>
      baseHandlers(input, (path) => {
        if (path.endsWith("/videos")) return okJson({ videos: [tailVideo] });
        if (path.endsWith("/videos/vid-tail")) {
          return okJson({
            video: tailVideo,
            transcript: { status: "AVAILABLE", text: "Segment text." },
            note: {
              status: "UNAVAILABLE",
              reason_code: "NOT_GENERATED",
              v2: { status: "UNAVAILABLE" },
            },
            scoring: { status: "UNAVAILABLE" },
            summary_read: { status: "UNAVAILABLE" },
            transcription: { status: "UNAVAILABLE" },
            intelligence_result: {
              status: "UNAVAILABLE",
              has_new_intelligence: false,
              intelligence_id: null,
              revision_id: null,
            },
            local_intelligence: { request_state: "UNKNOWN", eligibility: "UNAVAILABLE" },
            deep_analysis: { availability: "NOT_QUALIFIED" },
            workspace_ai_capabilities: { visual_analysis_eligible: false },
            visual_analysis: null,
            history: [],
          });
        }
        if (path.endsWith("/videos/vid-tail/deep-analysis")) {
          return okJson({ availability: "NOT_QUALIFIED" });
        }
        if (path.endsWith("/videos/vid-tail/evidence")) {
          return okJson({ evidence: base21 });
        }
        if (path.includes("/videos/vid-tail/evidence?evidence_id=ev-31")) {
          return okJson({
            evidence: [...base21, tail31],
            target_evidence_status: "FOUND",
            target_evidence_id: "ev-31",
          });
        }
        if (path.includes("/videos/vid-tail/evidence?evidence_id=ev-stale")) {
          return okJson({
            evidence: base21,
            target_evidence_status: "MISSING_OR_STALE",
            target_evidence_id: "ev-stale",
            target_evidence_reason: "目标证据片段已过期或原文被修改。",
          });
        }
        return null;
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const scrollSpy = vi.fn();
    const origScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollIntoView");
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: scrollSpy,
    });
    try {
      location.hash = "#Content/vid-tail/Evidence/ev-31";
      render(<App />);
      expect(await screen.findByText("尾段三十一关键依据")).toBeTruthy();
      await waitFor(() => {
        expect(document.getElementById("content-evidence-ev-31")).not.toBeNull();
      });

      cleanup();
      location.hash = "#Content/vid-tail/Evidence/ev-stale";
      render(<App />);
      const missingBanner = await screen.findByTestId("targeted-evidence-missing");
      expect(missingBanner.textContent).toContain("目标证据片段已过期或原文被修改");
    } finally {
      if (origScroll) Object.defineProperty(HTMLElement.prototype, "scrollIntoView", origScroll);
      else Reflect.deleteProperty(HTMLElement.prototype, "scrollIntoView");
    }
  });

  it("P1-08 & P1-09: Settings restore submits >32 KiB backup JSON and renders visual_images + warnings", async () => {
    const postedBodies: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/restore") && init?.method === "POST") {
          postedBodies.push(String(init.body ?? ""));
          return okJson({
            restored: {
              briefs: 2,
              weekly_briefs: 0,
              research_sessions: 20,
              curation_states: 1,
              visual_images: 3,
            },
            missing_visual_images: 1,
            warnings: ["注意：有 1 张历史快照关键帧缺少物理图片，导出时已自动略过损坏引用。"],
          });
        }
        return baseHandlers(input);
      }),
    );

    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel />
      </UiLanguageProvider>,
    );

    const bigPayload = JSON.stringify({
      schema_version: "workspace-ai-backup-v1",
      research_qa_sessions: Array.from({ length: 20 }, (_, i) => ({
        session_id: `s-${i}`,
        question: `Q-${i} ` + "x".repeat(2200),
      })),
    });
    expect(bigPayload.length).toBeGreaterThan(41545);

    const file = new File([bigPayload], "large-backup.json", { type: "application/json" });
    Object.defineProperty(file, "text", { value: async () => bigPayload });
    const inputEl = screen.getByLabelText("导入 AI 知识库快照文件") as HTMLInputElement;
    fireEvent.change(inputEl, { target: { files: [file] } });

    const statusNode = await screen.findByText(/已恢复 2 条中文摘要.*20 条跨视频问答记录/);
    expect(statusNode.textContent).toContain("3 张关键帧图片");
    expect(statusNode.textContent).toContain("缺少物理图片");
    expect(postedBodies[0].length).toBeGreaterThan(41545);
  });

  it("P1-12: #Content paginates >200 items via Load more + ?q= search and Cmd+K searches full library", async () => {
    const page1 = Array.from({ length: 200 }, (_, i) => makeVideoItem(i + 1));
    const page2 = Array.from({ length: 5 }, (_, i) => makeVideoItem(i + 201));
    const item501 = makeVideoItem(501, {
      video_id: "vid-501",
      title: "星云尾项501",
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        baseHandlers(input, (path) => {
          if (path.endsWith("/videos")) {
            return okJson({
              videos: page1,
              pagination: {
                limit: 200,
                offset: 0,
                total_count: 501,
                returned_count: 200,
                has_more: true,
              },
            });
          }
          if (path.includes("/videos?limit=200&offset=200")) {
            return okJson({
              videos: page2,
              pagination: {
                limit: 200,
                offset: 200,
                total_count: 501,
                returned_count: 200,
                has_more: true,
              },
            });
          }
          if (path.includes("q=%E6%98%9F%E4%BA%91%E5%B0%BE%E9%A1%B9501")) {
            return okJson({
              videos: [item501],
              pagination: {
                limit: 100,
                offset: 0,
                total_count: 1,
                returned_count: 1,
                has_more: false,
                q: "星云尾项501",
              },
            });
          }
          return null;
        }),
      ),
    );

    location.hash = "#Content";
    render(<App />);

    const loadMoreBtn = await screen.findByRole("button", {
      name: /加载更多内容 \(已显示 200 \/ 共 501\)/,
    });
    fireEvent.click(loadMoreBtn);
    expect(await screen.findByText("Library Video 201")).toBeTruthy();

    const searchBox = screen.getByRole("searchbox");
    fireEvent.change(searchBox, { target: { value: "星云尾项501" } });
    expect(await screen.findByText("星云尾项501")).toBeTruthy();

    // Open Cmd+K and verify search finds item #501
    fireEvent.change(searchBox, { target: { value: "" } });
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const paletteDialog = await screen.findByRole("dialog");
    const cmdInput = within(paletteDialog).getByRole("combobox");
    fireEvent.change(cmdInput, { target: { value: "星云尾项501" } });
    expect(await within(paletteDialog).findByText("星云尾项501")).toBeTruthy();
  }, 20_000);

  it("P1-15: Cmd+K topic handoff clears locked multi-video comparison and asks under the new topic", async () => {
    const askPayloads: Record<string, unknown>[] = [];
    const vids = [
      makeVideoItem(1, { video_id: "vid-old-1", title: "Old Compare 1" }),
      makeVideoItem(2, { video_id: "vid-old-2", title: "Old Compare 2" }),
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) =>
        baseHandlers(input, (path) => {
          if (path.endsWith("/videos")) return okJson({ videos: vids });
          if (path.endsWith("/topics")) {
            return okJson({
              topics: [
                {
                  topic_id: "tp-new-beta",
                  name: "新专题Beta",
                  pinned: false,
                  lifecycle: "ACTIVE",
                  current_state: "CONFIRMED",
                  independence: "INDEPENDENT",
                  contributions: [],
                  timeline: [],
                  ai_evolution: { video_count: 1, must_watch_count: 1 },
                },
              ],
            });
          }
          if (path.endsWith("/workspace-ai/research/sessions") && (!init?.method || init.method === "GET")) {
            return okJson({
              sessions: [],
              suggested_questions: [],
              scope_options: {
                channels: [{ key: "Scale Lab", label: "Scale Lab", count: 2 }],
                topic_clusters: [
                  { name: "旧专题Alpha", count: 1 },
                  { name: "新专题Beta", count: 1 },
                ],
                starred_count: 1,
                videos: vids.map((v) => ({
                  video_id: v.video_id,
                  title: v.title,
                  channel_name: v.channel_name,
                  score: 8.5,
                  topic_cluster_zh: v.ai_brief.topic_cluster_zh,
                  starred: v.ai_brief.starred,
                })),
              },
            });
          }
          if (path.endsWith("/workspace-ai/research/ask") && init?.method === "POST") {
            askPayloads.push(JSON.parse(String(init.body ?? "{}")));
            return okJson({
              session: {
                session_id: "sess-topic-new",
                question: "新专题核心结论？",
                answer_zh: "来自新专题Beta[E1]",
                answer_status: "GROUNDED",
                key_takeaways_zh: ["Beta 结论[E1]"],
                action_items_zh: [],
                citations: [
                  {
                    ref: "E1",
                    evidence_id: "ev-b1",
                    video_id: "vid-old-2",
                    video_title: "Old Compare 2",
                    channel_name: "Scale Lab",
                    locator_type: "TIME_RANGE",
                    start_seconds: 10,
                    end_seconds: 20,
                    excerpt: "Beta 原话",
                    why_relevant_zh: "直接相关",
                    verified: true,
                  },
                ],
                scope: { topic_cluster: "新专题Beta" },
                scope_label_zh: "专题：新专题Beta",
                obsidian_markdown: "# Beta",
                pinned: false,
                created_at: "2026-11-23T15:10:00Z",
              },
            });
          }
          return null;
        }),
      ),
    );

    setPendingResearchVideoIds(["vid-old-1", "vid-old-2"]);
    location.hash = "#Research";
    render(<App />);

    expect(await screen.findByText(/已锁定 2 篇指定源视频/)).toBeTruthy();

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const paletteDialog = await screen.findByRole("dialog");
    const cmdInput = within(paletteDialog).getByRole("combobox");
    fireEvent.change(cmdInput, { target: { value: "新专题Beta" } });
    fireEvent.click(await within(paletteDialog).findByRole("option", { name: /围绕专题追问：新专题Beta/ }));

    await waitFor(() => {
      expect(screen.queryByText(/已锁定 2 篇指定源视频/)).toBeNull();
    });
    const topicSelect = screen.getByLabelText("限定专题") as HTMLSelectElement;
    expect(topicSelect.value).toBe("新专题Beta");

    const askInput = screen.getByLabelText("跨视频提问");
    fireEvent.change(askInput, { target: { value: "新专题核心结论？" } });
    fireEvent.submit(askInput.closest("form")!);

    await waitFor(() => expect(askPayloads).toHaveLength(1));
    expect(askPayloads[0].topic_cluster).toBe("新专题Beta");
    expect(askPayloads[0].video_ids).toBeUndefined();
  });

  it("P2-03: Visual Lightbox preserves state across cloned re-renders, traps Tab focus, and restores trigger focus on Esc", async () => {
    const analysis1 = makeVisualAnalysis();
    const view = render(
      <UiLanguageProvider>
        <WorkspaceVisualKeyframePanel
          videoId="vid-kf-1"
          isLocalVideo={true}
          ffmpegAvailable={true}
          visualAnalysis={analysis1}
          onCompleted={vi.fn()}
        />
      </UiLanguageProvider>,
    );

    const card1 = screen.getByRole("button", { name: /三层系统架构图/ });
    card1.focus();
    fireEvent.click(card1);

    const dialog = await screen.findByRole("dialog");
    const closeBtn = within(dialog).getByRole("button", { name: /关闭/ });
    expect(document.activeElement).toBe(closeBtn);

    view.rerender(
      <UiLanguageProvider>
        <WorkspaceVisualKeyframePanel
          videoId="vid-kf-1"
          isLocalVideo={true}
          ffmpegAvailable={true}
          visualAnalysis={makeVisualAnalysis()}
          onCompleted={vi.fn()}
        />
      </UiLanguageProvider>,
    );
    expect(screen.getByRole("dialog")).toBeTruthy();

    const nextBtn = within(screen.getByRole("dialog")).getByRole("button", { name: /下一帧/ });
    closeBtn.focus();
    fireEvent.keyDown(window, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(nextBtn);

    fireEvent.keyDown(window, { key: "Tab" });
    expect(document.activeElement).toBe(closeBtn);

    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(document.activeElement).toBe(card1);
  });

  it("P2-04: Cmd+K ignores Enter during IME composition and executes cleanly after compositionEnd", async () => {
    vi.stubGlobal("fetch", vi.fn((input: string) => baseHandlers(input)));
    location.hash = "#Home";
    render(<App />);
    await screen.findByRole("button", { name: "设置" });

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const cmdInput = await screen.findByRole("combobox");
    fireEvent.change(cmdInput, { target: { value: "设置" } });

    fireEvent.compositionStart(cmdInput);
    fireEvent.keyDown(cmdInput, { key: "Enter" });
    expect(screen.getByRole("dialog")).toBeTruthy();
    expect(location.hash).toBe("#Home");

    fireEvent.compositionEnd(cmdInput);
    fireEvent.keyDown(cmdInput, { key: "Enter", isComposing: true });
    expect(location.hash).toBe("#Home");

    fireEvent.keyDown(cmdInput, { key: "Enter" });
    await waitFor(() => expect(location.hash).toBe("#Settings"));
  });

  it("P2-05: Same-page pending research session switch activates target session immediately", async () => {
    const sess1 = {
      session_id: "sess-01",
      question: "问题一：架构亮点？",
      answer_zh: "回答一：双库隔离。",
      answer_status: "GROUNDED",
      key_takeaways_zh: ["双库隔离"],
      action_items_zh: [],
      citations: [],
      scope: {},
      scope_label_zh: "全库",
      obsidian_markdown: "# S1",
      pinned: false,
      created_at: "2026-11-23T15:00:00Z",
    };
    const sess2 = {
      session_id: "sess-02",
      question: "问题二：冷读优化？",
      answer_zh: "回答二：按页精准读取非 Markdown 摘要。",
      answer_status: "GROUNDED",
      key_takeaways_zh: ["按页读取"],
      action_items_zh: [],
      citations: [],
      scope: {},
      scope_label_zh: "全库",
      obsidian_markdown: "# S2",
      pinned: false,
      created_at: "2026-11-23T14:50:00Z",
    };
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        baseHandlers(input, (path) => {
          if (path.endsWith("/videos")) return okJson({ videos: [makeVideoItem(1)] });
          if (path.endsWith("/workspace-ai/research/sessions")) {
            return okJson({
              sessions: [sess1, sess2],
              suggested_questions: [],
              scope_options: { channels: [], topic_clusters: [], starred_count: 0, videos: [] },
            });
          }
          return null;
        }),
      ),
    );

    location.hash = "#Research";
    render(<App />);
    expect(await screen.findByText("回答一：双库隔离。")).toBeTruthy();

    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const cmdInput = await screen.findByRole("combobox");
    fireEvent.change(cmdInput, { target: { value: "冷读优化" } });
    fireEvent.click(await screen.findByRole("option", { name: /问题二：冷读优化/ }));

    expect(await screen.findByText("回答二：按页精准读取非 Markdown 摘要。")).toBeTruthy();
  });

  it("N10: #Content search pagination loads page 2 and Cmd+K displays match truncation notice", async () => {
    const initial200 = Array.from({ length: 200 }, (_, i) => makeVideoItem(i + 1));
    const searchPage1 = Array.from({ length: 100 }, (_, i) =>
      makeVideoItem(1000 + i, { title: `量子检索命中-${i + 1}` }),
    );
    const searchPage2 = [
      makeVideoItem(1140, { title: "量子检索尾页-101" }),
    ];
    const requestedUrls: string[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        requestedUrls.push(input);
        return baseHandlers(input, (path) => {
          if (path.endsWith("/videos")) return okJson({ videos: initial200 });
          if (path.includes("/videos?limit=200&offset=0")) {
            return okJson({
              videos: initial200,
              pagination: {
                limit: 200,
                offset: 0,
                total_count: 520,
                returned_count: 200,
                has_more: true,
              },
            });
          }
          if (path.includes("/videos?q=") && path.includes("limit=100&offset=0")) {
            return okJson({
              videos: searchPage1,
              pagination: {
                limit: 100,
                offset: 0,
                total_count: 140,
                returned_count: 100,
                has_more: true,
              },
            });
          }
          if (path.includes("/videos?q=") && path.includes("limit=100&offset=100")) {
            return okJson({
              videos: searchPage2,
              pagination: {
                limit: 100,
                offset: 100,
                total_count: 140,
                returned_count: 1,
                has_more: false,
              },
            });
          }
          if (path.includes("/videos?q=") && path.includes("limit=50&offset=0")) {
            return okJson({
              videos: searchPage1.slice(0, 50),
              pagination: {
                limit: 50,
                offset: 0,
                total_count: 85,
                returned_count: 50,
                has_more: true,
              },
            });
          }
          return null;
        });
      }),
    );

    location.hash = "#Content";
    render(<App />);
    const searchBox = await screen.findByRole("searchbox");
    fireEvent.change(searchBox, { target: { value: "量子检索" } });

    const loadMoreSearchBtn = await screen.findByRole("button", {
      name: /加载更多搜索结果.*100 \/ 共 140/,
    });
    expect(loadMoreSearchBtn).toBeTruthy();

    fireEvent.click(loadMoreSearchBtn);
    expect(await screen.findByText("量子检索尾页-101")).toBeTruthy();

    fireEvent.change(searchBox, { target: { value: "" } });
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const dialog = await screen.findByRole("dialog");
    const cmdInput = within(dialog).getByRole("combobox");
    fireEvent.change(cmdInput, { target: { value: "量子检索" } });

    expect(
      await within(dialog).findByText(/库内命中共 85 条/),
    ).toBeTruthy();
    expect(requestedUrls.some((u) => u.includes("limit=100&offset=100"))).toBe(true);
  }, 20_000);

  it("Round2 P1-2 & P2-13: 2s polling preserves page 2 and remote search, and CommandPalette clears stale counts", async () => {
    const page1 = [
      makeVideoItem(1, { processing_status: "FETCHING", title: "Processing Video #1" }),
      ...Array.from({ length: 199 }, (_, i) => makeVideoItem(i + 2)),
    ];
    const page2 = [makeVideoItem(201, { title: "Kept Page 2 Item" })];
    const searchHits = [makeVideoItem(301, { video_id: "vid-search-301", title: "AlphaHitRemote" })];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        const path = input.toString();
        return baseHandlers(path, (p) => {
          if (p.endsWith("/videos")) {
            return okJson({
              videos: page1,
              pagination: {
                limit: 200,
                offset: 0,
                total_count: 350,
                returned_count: 200,
                has_more: true,
              },
            });
          }
          if (p.includes("/videos?limit=200&offset=200")) {
            return okJson({
              videos: page2,
              pagination: {
                limit: 200,
                offset: 200,
                total_count: 350,
                returned_count: 1,
                has_more: false,
              },
            });
          }
          if (p.includes("q=Alpha")) {
            return okJson({
              videos: searchHits,
              pagination: {
                limit: 100,
                offset: 0,
                total_count: 85,
                returned_count: 1,
                has_more: true,
                q: "Alpha",
              },
            });
          }
          if (p.includes("q=Beta")) {
            return new Promise<Response>(() => {});
          }
          return null;
        });
      }),
    );

    location.hash = "#Content";
    render(<App />);

    const loadMoreBtn = await screen.findByRole("button", {
      name: /加载更多内容 \(已显示 200 \/ 共 350\)/,
    });
    fireEvent.click(loadMoreBtn);
    expect(await screen.findByText("Kept Page 2 Item")).toBeTruthy();

    // Wait >2.3s for the 2-second processing poll tick and verify Page 2 stays mounted.
    await new Promise((r) => setTimeout(r, 2300));
    expect(screen.getByText("Kept Page 2 Item")).toBeTruthy();

    const searchBox = screen.getByRole("searchbox");
    fireEvent.change(searchBox, { target: { value: "Alpha" } });
    expect(await screen.findByText("AlphaHitRemote")).toBeTruthy();
    await new Promise((r) => setTimeout(r, 2300));
    expect(screen.getByText("AlphaHitRemote")).toBeTruthy();

    // Open Cmd+K, trigger Alpha remote count (85), then switch to Beta (pending): stale 85 must disappear immediately.
    fireEvent.change(searchBox, { target: { value: "" } });
    fireEvent.keyDown(window, { key: "k", metaKey: true });
    const dialog = await screen.findByRole("dialog");
    const cmdInput = within(dialog).getByRole("combobox");
    fireEvent.change(cmdInput, { target: { value: "Alpha" } });
    expect(await within(dialog).findByText(/库内命中共 85 条/)).toBeTruthy();
    fireEvent.change(cmdInput, { target: { value: "Beta" } });
    expect(within(dialog).queryByText(/库内命中共 85 条/)).toBeNull();
  }, 30_000);

  it("Round2 P2-13: completing onboarding in Demo mode does not skip real empty workspace onboarding", async () => {
    localStorage.clear();
    localStorage.setItem("yia.ui-language", "zh-CN");
    let demoModeFlag = true;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) =>
        baseHandlers(input.toString(), (path) => {
          if (path.endsWith("/dashboard")) {
            return okJson({
              intelligence: [],
              saved_intelligence_ids: [],
              pinned_topics: [],
              weekly_v1: [],
              needs_attention: [],
              operations: { source_count: 0 },
              demo_mode: demoModeFlag,
            });
          }
          return null;
        }),
      ),
    );

    location.hash = "#Home";
    render(<App />);
    const skipBtn = await screen.findByRole("button", { name: /暂时跳过|Skip for now/ });
    fireEvent.click(skipBtn);
    expect(localStorage.getItem("intelligence.onboarding.completed.demo.v1")).toBe("true");
    expect(localStorage.getItem("intelligence.onboarding.completed.v1")).toBeNull();

    cleanup();
    demoModeFlag = false;
    render(<App />);
    expect(await screen.findByRole("button", { name: /暂时跳过|Skip for now/ })).toBeTruthy();
  });
});
