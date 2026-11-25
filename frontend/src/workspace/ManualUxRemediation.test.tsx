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
import { LocalImport } from "./LocalImport";
import { InlineYouTubeAuthRecovery } from "./ReaderRecoveryPanel";
import { ReaderReferenceDrawer } from "./ReaderReferenceDrawer";
import {
  WhisperQuickDownloadPanel,
  WorkspaceAiSettingsPanel,
  YouTubeAuthSettingsPanel,
} from "./WorkspaceAiWidgets";
import { onboardingReturnStepKey } from "./Onboarding";
import { UiLanguageProvider } from "./uiLanguage";

const okJson = (body: unknown, status = 200) =>
  Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response);

const CURATED_OLLAMA_MOCK = [
  {
    id: "qwen3:8b",
    label: "Qwen3 8B（最推荐）",
    label_en: "Qwen3 8B (Recommended)",
    size_label: "5.2 GB",
    ram_label_zh: "建议 ≥16 GB 内存",
    ram_label_en: "16 GB+ RAM",
    tier: "recommended",
    reason_zh: "中文理解与长视频结构化总结均衡稳定",
    reason_en: "Balanced Chinese & long-video summary quality",
  },
  {
    id: "qwen3:4b",
    label: "Qwen3 4B（轻量高速）",
    label_en: "Qwen3 4B (Fast & Light)",
    size_label: "2.6 GB",
    ram_label_zh: "8 GB 内存可流畅跑",
    ram_label_en: "Runs smoothly on 8 GB RAM",
    tier: "lightweight",
    reason_zh: "低占用入门首选",
    reason_en: "Lightweight starter model",
  },
];

const CURATED_WHISPER_MOCK = [
  {
    id: "mlx-community/whisper-large-v3-turbo",
    slug: "whisper-large-v3-turbo",
    label: "Whisper Large V3 Turbo",
    size_label: "1.5 GB",
    tier: "recommended",
    summary_zh: "中英混讲精度高、速度极快",
    summary_en: "High accuracy & fast Apple Silicon speed",
  },
  {
    id: "mlx-community/whisper-small-mlx",
    slug: "whisper-small-mlx",
    label: "Whisper Small（轻量版）",
    size_label: "480 MB",
    tier: "lightweight",
    summary_zh: "体积小巧、快速试用",
    summary_en: "Compact starter speech model",
  },
];

function makeBaseSettings(workspaceAiOverrides: Record<string, unknown> = {}) {
  return {
    general: {
      timezone: "Asia/Shanghai",
      output_language: "zh-CN",
      output_language_source: "BOOTSTRAP_DEFAULT",
      output_language_updated_at: null,
    },
    providers: [],
    workspace_ai: {
      active_mode: "local_ollama",
      ollama_base_url: "http://127.0.0.1:11434",
      ollama_model: "qwen3:8b",
      ollama_reachable: true,
      installed_ollama_models: [],
      cloud_provider: "deepseek",
      cloud_base_url: "https://api.deepseek.com/v1",
      cloud_model: "deepseek-chat",
      cloud_key_configured: false,
      cloud_daily_call_limit: 5,
      cloud_calls_today: 0,
      extractive_available: true,
      local_mlx_Whisper_ready: false,
      active_whisper_slug: null,
      curated_installed_ollama_models: CURATED_OLLAMA_MOCK,
      curated_whisper_models: CURATED_WHISPER_MOCK,
      ...workspaceAiOverrides,
    },
  };
}

function baseFetch(input: string, extra?: (path: string, init?: RequestInit) => Promise<Response> | null, init?: RequestInit) {
  if (extra) {
    const hit = extra(input, init);
    if (hit) return hit;
  }
  if (input.endsWith("/system")) {
    return okJson({ release_posture: "PUBLIC_BETA", capabilities: {} });
  }
  if (input.endsWith("/dashboard")) {
    return okJson({
      counts: { videos: 0, organized: 0, sources: 0, intelligence: 0 },
      operations: { source_count: 0 },
      needs_attention: [],
      intelligence: [],
      pinned_topics: [],
    });
  }
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
  if (input.endsWith("/settings/cloud-spending-policy")) {
    return okJson({
      spending_policy: { enabled: false, revision: 1, total_cny: 0, per_request_cny: 0, max_calls: 0 },
    });
  }
  if (input.endsWith("/settings")) return okJson(makeBaseSettings());
  if (input.endsWith("/workspace-ai/settings")) {
    return okJson(makeBaseSettings().workspace_ai);
  }
  if (input.endsWith("/workspace-ai/youtube-auth")) {
    return okJson({
      enabled: false,
      auth_mode: "disabled",
      browser_name: "",
      supported_browsers: ["chrome", "firefox", "edge", "brave", "safari"],
      cookie_configured: false,
      daily_limit: 20,
      used_today: 0,
      cooldown_seconds: 15,
      circuit_open: false,
      circuit_open_until: "",
    });
  }
  if (input.endsWith("/workspace-ai/ollama/pull-status")) return okJson({ state: "idle" });
  if (input.endsWith("/workspace-ai/whisper/download-status")) return okJson({ state: "idle" });
  if (input.endsWith("/local/transcription/capability")) {
    return okJson({ state: "MODEL_MISSING", available: false });
  }
  if (input.endsWith("/creator-following/capability")) return okJson({ supported: false });
  if (input.endsWith("/preferences")) return okJson({ active: null, history: [] });
  if (input.endsWith("/topics")) return okJson({ topics: [] });
  if (input.endsWith("/sources")) return okJson({ sources: [] });
  if (input.endsWith("/intelligence")) return okJson({ intelligence: [], activity: [] });
  if (input.endsWith("/saved-intelligence")) return okJson({ saved: [] });
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

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  localStorage.setItem("yia.ui-language", "zh-CN");
  location.hash = "";
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
  location.hash = "";
});

describe("Manual UX Remediation (#1-#4)", () => {
  it("#1: preserves onboarding when jumping to #Settings/models/bigmodel, auto-opens & refreshes models, and resumes Step 2 -> Step 3 on return", async () => {
    let liveModelsFetched = 0;
    location.hash = "#Home";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) =>
        baseFetch(
          input,
          (path) => {
            if (path.endsWith("/workspace-ai/settings")) {
              liveModelsFetched += 1;
              return okJson(
                makeBaseSettings({
                  ollama_reachable: true,
                  installed_ollama_models: ["qwen3:8b", "llama3.1:8b"],
                }).workspace_ai,
              );
            }
            return null;
          },
          init,
        ),
      ),
    );

    render(<App />);

    // Step 1 -> Step 2 on Home
    const nextBtn = await screen.findByRole("button", { name: "继续" });
    fireEvent.click(nextBtn);
    expect(document.body.textContent).toContain("对话总结用 AI 模型；本地语音转写仅导入无字幕音视频时需要");

    // Jump to #Settings/models/bigmodel MUST preserve onboarding (NOT complete it!)
    const modelSetupLink = screen.getByRole("link", { name: "配置总结模型（本地 / 云端）" });
    expect(modelSetupLink.getAttribute("href")).toBe("#Settings/models/bigmodel");
    fireEvent.click(modelSetupLink);
    if (!location.hash.startsWith("#Settings/models")) {
      location.hash = "#Settings/models/bigmodel";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    }

    expect(localStorage.getItem("intelligence.onboarding.completed.v1")).toBeNull();
    expect(sessionStorage.getItem(onboardingReturnStepKey)).toBe("1");

    // #Settings/models/bigmodel auto-opens WorkspaceAiSettingsPanel, fetches live Ollama models, and shows return banner
    const returnBanner = await screen.findByRole("region", { name: "新手引导进度" });
    expect(returnBanner.textContent).toContain("不会丢失进度");
    expect(returnBanner.textContent).toContain("继续第 3 步");
    await waitFor(() => expect(liveModelsFetched).toBeGreaterThanOrEqual(1));
    expect(await screen.findByRole("option", { name: /qwen3:8b/i })).toBeTruthy();

    // Return to #Home via banner -> resumes Step 2 cleanly and advances to Step 3 (with Bilibili no-VPN info)
    const backLink = within(returnBanner).getByRole("link", { name: /返回新手引导继续第 3 步/ });
    fireEvent.click(backLink);
    if (location.hash !== "#Home") {
      location.hash = "#Home";
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    }

    expect(await screen.findByRole("link", { name: "配置总结模型（本地 / 云端）" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "继续" }));
    expect(document.body.textContent).toContain("无需 VPN");
    expect(screen.getByRole("button", { name: "添加内容" })).toBeTruthy();
  });

  it("#2 & #4: triggers 1-click Ollama pull and domestic-first Cloud BYOK test connection", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Settings/models/bigmodel";
    let pullPolls = 0;
    const testedPayloads: Record<string, unknown>[] = [];
    const pulledModels: string[] = [];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/ollama/pull") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body ?? "{}"));
          pulledModels.push(String(parsed.model));
          return okJson({
            state: "pulling",
            model: parsed.model,
            status_text: "正在下载…",
            completed_bytes: 100,
            total_bytes: 200,
            percent: 50,
            error: null,
          });
        }
        if (input.endsWith("/workspace-ai/ollama/pull-status")) {
          pullPolls += 1;
          if (pullPolls === 1) {
            return okJson({
              state: "succeeded",
              model: "qwen3:8b",
              status_text: "已下载并自动启用",
              completed_bytes: 200,
              total_bytes: 200,
              percent: 100,
              error: null,
            });
          }
          return okJson({ state: "idle" });
        }
        if (input.endsWith("/workspace-ai/settings") && (!init?.method || init.method === "GET")) {
          return okJson(makeBaseSettings({ installed_ollama_models: ["qwen3:4b"] }).workspace_ai);
        }
        if (input.endsWith("/workspace-ai/test-cloud") && init?.method === "POST") {
          testedPayloads.push(JSON.parse(String(init.body ?? "{}")));
          return okJson({ ok: true, latency_ms: 35, message: "连接成功，API Key 有效" });
        }
        return okJson({});
      }),
    );

    render(
      <UiLanguageProvider>
        <WorkspaceAiSettingsPanel initial={makeBaseSettings({ installed_ollama_models: [] }).workspace_ai as never} />
      </UiLanguageProvider>,
    );

    // 1. Trigger curated Ollama download
    const pullBtns = await screen.findAllByRole("button", { name: "一键下载并启用" });
    expect(pullBtns.length).toBeGreaterThanOrEqual(1);
    fireEvent.click(pullBtns[0]);
    await waitFor(() => expect(pulledModels.length).toBe(1));
    expect(pulledModels[0].length).toBeGreaterThan(0);

    // 2. Switch to Cloud BYOK -> verify DeepSeek (CN Direct) first, 3-step guide, and zero-token Test Connection
    const modeSelect = screen.getByRole("combobox", { name: "运行模式" });
    fireEvent.change(modeSelect, { target: { value: "cloud_byok" } });

    const providerSelect = await screen.findByRole("combobox", { name: "云端服务商预设" });
    const firstOption = within(providerSelect).getAllByRole("option")[0];
    expect(firstOption.textContent).toContain("DeepSeek（国内直连");
    expect(screen.getByRole("list", { name: "3 步配置云端模型" })).toBeTruthy();

    const apiKeyInput = screen.getByLabelText(/云端 API Key/);
    fireEvent.change(apiKeyInput, { target: { value: "sk-cn-test-123" } });

    fireEvent.click(screen.getByRole("button", { name: "测试连接" }));
    await waitFor(() => expect(testedPayloads.length).toBe(1));
    expect(testedPayloads[0]).toMatchObject({
      cloud_base_url: "https://api.deepseek.com/v1",
      cloud_api_key: "sk-cn-test-123",
    });
    expect(await screen.findByText("连接成功，API Key 有效")).toBeTruthy();
  });

  it("#2 & #4: WhisperQuickDownloadPanel lets Mainland users choose CN mirror and trigger 1-click download", async () => {
    const requests: Array<{ model_id: string; mirror: string }> = [];
    const onReady = vi.fn();

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/whisper/download") && init?.method === "POST") {
          requests.push(JSON.parse(String(init.body ?? "{}")));
          return okJson({
            state: "downloading",
            model_id: "mlx-community/whisper-large-v3-turbo",
            slug: "whisper-large-v3-turbo",
            mirror: "cn_mirror",
            mirror_used: "https://hf-mirror.com",
            current_file: "config.json",
            completed_files: 0,
            total_files: 2,
            percent: 10,
            error: null,
          });
        }
        if (input.endsWith("/workspace-ai/whisper/download-status")) {
          return okJson({
            state: "succeeded",
            model_id: "mlx-community/whisper-large-v3-turbo",
            slug: "whisper-large-v3-turbo",
            mirror: "cn_mirror",
            mirror_used: "https://hf-mirror.com",
            current_file: "已就绪并自动完成配置",
            completed_files: 2,
            total_files: 2,
            percent: 100,
            error: null,
          });
        }
        return okJson({});
      }),
    );

    render(
      <UiLanguageProvider>
        <WhisperQuickDownloadPanel
          ready={false}
          activeSlug={null}
          catalog={CURATED_WHISPER_MOCK}
          onReady={onReady}
        />
      </UiLanguageProvider>,
    );

    const mirrorSelect = screen.getByRole("combobox", { name: "语音模型下载线路" });
    fireEvent.change(mirrorSelect, { target: { value: "cn_mirror" } });

    const downloadBtns = screen.getAllByRole("button", { name: "一键下载并自动配置" });
    fireEvent.click(downloadBtns[0]);

    await waitFor(() =>
      expect(requests).toEqual([
        { model_id: "mlx-community/whisper-large-v3-turbo", mirror: "cn_mirror" },
      ]),
    );
    await waitFor(() => expect(onReady).toHaveBeenCalled());
  });

  it("#3 & #4: PendingYouTubeVideoDetail separates network failures (no login CTA) from bot checks (Option B CTA)", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");

    const makePendingDetail = (videoId: string, errCode: string) => ({
      video: {
        video_id: videoId,
        work_kind: "IMPORT_VIDEO",
        source_id: `src-${videoId}`,
        provider: "YOUTUBE",
        title: `Pending ${videoId}`,
        source_url: `https://www.youtube.com/watch?v=${videoId}`,
        published_at: "2026-11-24T10:00:00Z",
        processing_status: "NEEDS_ATTENTION",
        import_error_code: errCode,
        retry_allowed: true,
        can_remove_pending: true,
      },
      transcript: { status: "NOT_AVAILABLE" },
      note: { v2: { status: "UNAVAILABLE" } },
      scoring: { status: "NOT_AVAILABLE" },
      intelligence_result: { status: "UNAVAILABLE" },
      history: [],
    });

    let activeErrCode = "YOUTUBE_NETWORK_UNAVAILABLE";
    let activeVideoId = "vidNetNoVpn";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) =>
        baseFetch(
          input,
          (path) => {
            if (path.endsWith(`/videos/${activeVideoId}`)) {
              return okJson(makePendingDetail(activeVideoId, activeErrCode));
            }
            if (path.endsWith("/videos")) {
              return okJson({ videos: [makePendingDetail(activeVideoId, activeErrCode).video] });
            }
            return null;
          },
          init,
        ),
      ),
    );

    // 1. Network unavailable -> honest network diagnosis, NO bot verification wording, NO YouTube auth button
    location.hash = `#Content/${activeVideoId}`;
    const { unmount } = render(<App />);

    expect(
      await screen.findByText(/当前网络或系统代理未能连接到 YouTube（连接超时或网络不可达，并非账号被拦截）/),
    ).toBeTruthy();
    expect(document.body.textContent).toContain("无 VPN 环境下也可直接导入 B 站公开视频");
    expect(document.body.textContent).not.toContain("机器人验证");
    expect(screen.queryByRole("link", { name: /授权本人 YouTube 登录态/ })).toBeNull();
    unmount();

    // 2. Auth gate -> shows Option B #Settings/youtube-auth CTA while preserving retry & local import
    activeErrCode = "YOUTUBE_AUTH_REQUIRED";
    activeVideoId = "vidBotGate2";
    location.hash = `#Content/${activeVideoId}`;
    render(<App />);

    expect(
      await screen.findByText(/YouTube 当前对该链接触发了匿名访问与机器人验证限制/),
    ).toBeTruthy();
    const authCta = screen.getByRole("link", { name: "授权本人 YouTube 登录态 ›" });
    expect(authCta.getAttribute("href")).toBe(
      `#Settings/youtube-auth?return=${encodeURIComponent("#Content/vidBotGate2")}`,
    );
    expect(screen.getByRole("button", { name: "重新尝试获取" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "改用本地文件导入" })).toBeTruthy();
  });

  it("#3 Option B: YouTubeAuthSettingsPanel configures browser fallback and supports 1-click disconnect", async () => {
    const putBodies: Record<string, unknown>[] = [];
    let disconnected = false;

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/youtube-auth/disconnect") && init?.method === "POST") {
          disconnected = true;
          return okJson({
            enabled: false,
            auth_mode: "disabled",
            browser_name: "",
            supported_browsers: ["chrome", "firefox", "safari"],
            cookie_configured: false,
            daily_limit: 20,
            used_today: 0,
            cooldown_seconds: 15,
            circuit_open: false,
            circuit_open_until: "",
          });
        }
        if (input.endsWith("/workspace-ai/youtube-auth") && init?.method === "PUT") {
          const parsed = JSON.parse(String(init.body ?? "{}"));
          putBodies.push(parsed);
          return okJson({
            enabled: true,
            auth_mode: parsed.auth_mode,
            browser_name: parsed.browser_name ?? "chrome",
            supported_browsers: ["chrome", "firefox", "safari"],
            cookie_configured: false,
            daily_limit: parsed.daily_limit ?? 20,
            used_today: 0,
            cooldown_seconds: 15,
            circuit_open: false,
            circuit_open_until: "",
          });
        }
        if (input.endsWith("/workspace-ai/youtube-auth")) {
          return okJson({
            enabled: false,
            auth_mode: "disabled",
            browser_name: "",
            supported_browsers: ["chrome", "firefox", "safari"],
            cookie_configured: false,
            daily_limit: 20,
            used_today: 0,
            cooldown_seconds: 15,
            circuit_open: false,
            circuit_open_until: "",
          });
        }
        return okJson({});
      }),
    );

    render(
      <UiLanguageProvider>
        <YouTubeAuthSettingsPanel />
      </UiLanguageProvider>,
    );

    expect(await screen.findByText(/未启用（仅免登录直采/)).toBeTruthy();

    fireEvent.change(screen.getByRole("combobox", { name: "YouTube 兜底方式" }), {
      target: { value: "browser" },
    });
    fireEvent.change(await screen.findByRole("combobox", { name: "选择已登录 YouTube 的浏览器" }), {
      target: { value: "chrome" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存授权设置" }));

    await waitFor(() => expect(putBodies.length).toBe(1));
    expect(putBodies[0]).toMatchObject({
      enabled: true,
      auth_mode: "browser",
      browser_name: "chrome",
      daily_limit: 20,
    });
    expect(await screen.findByText(/已授权 · 本机 chrome/)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "断开全局备用授权" }));
    await waitFor(() => expect(disconnected).toBe(true));
    expect(await screen.findByText(/未启用（仅免登录直采/)).toBeTruthy();
  });

  it("P2-1: syncs consecutive star toggles inside Content remote search results", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Content";

    const primary200 = Array.from({ length: 200 }, (_, i) => ({
      video_id: `vid-lib-${String(i + 1).padStart(3, "0")}`,
      provider: "YOUTUBE",
      channel_id: "ch-main",
      channel_name: "Scale Lab",
      title: `Library Video ${i + 1}`,
      published_at: "2026-11-23T10:00:00Z",
      processing_status: "ORGANIZED",
      last_updated: "2026-11-23T10:00:00Z",
      duration_seconds: 900,
      ai_brief: {
        headline_zh: `核心结论 ${i + 1}`,
        summary_zh: `详细摘要 ${i + 1}`,
        score: 8.5,
        score_reason_zh: "高信息密度",
        recommendation_tier: "MUST_WATCH",
        content_bucket: "DEEP_DIVE",
        is_short_noise: false,
        starred: false,
        is_read: false,
        topics_zh: ["工程实践"],
        topic_cluster_zh: "工程实践",
      },
    }));
    let persistedStarred = false;
    const curationPosts: Array<Record<string, unknown>> = [];

    const makeTailItem = () => ({
      video_id: "vid-tail-201",
      provider: "YOUTUBE",
      channel_id: "ch-main",
      channel_name: "Scale Lab",
      title: "Target Star Item 201",
      published_at: "2026-11-23T10:00:00Z",
      processing_status: "ORGANIZED",
      last_updated: "2026-11-23T10:00:00Z",
      duration_seconds: 900,
      ai_brief: {
        headline_zh: "远端搜索收藏同步验证条目",
        summary_zh: "验证大库搜索内连续点击收藏的状态同步",
        score: 9.0,
        score_reason_zh: "高信息密度",
        recommendation_tier: "MUST_WATCH",
        content_bucket: "DEEP_DIVE",
        is_short_noise: false,
        starred: persistedStarred,
        is_read: false,
        topics_zh: ["工程实践"],
        topic_cluster_zh: "工程实践",
      },
    });

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.includes("/workspace-ai/videos/vid-tail-201/curation") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body ?? "{}"));
          curationPosts.push(parsed);
          if (typeof parsed.starred === "boolean") persistedStarred = parsed.starred;
          return okJson({ starred: persistedStarred, is_read: false });
        }
        if (input.includes("/videos?q=Target%20Star")) {
          return okJson({
            videos: [makeTailItem()],
            pagination: {
              limit: 100,
              offset: 0,
              total_count: 1,
              returned_count: 1,
              has_more: false,
              q: "Target Star",
            },
          });
        }
        if (input.endsWith("/videos") || input.includes("/videos?limit=200&offset=0")) {
          return okJson({
            videos: primary200,
            pagination: {
              limit: 200,
              offset: 0,
              total_count: 201,
              returned_count: 200,
              has_more: true,
            },
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);
    const searchBox = await screen.findByRole("searchbox");
    fireEvent.change(searchBox, { target: { value: "Target Star" } });

    expect(await screen.findByText("Target Star Item 201")).toBeTruthy();

    // First click -> star = true
    const starBtn1 = await screen.findByRole("button", { name: "收藏待看" });
    expect(starBtn1.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(starBtn1);

    await waitFor(() => expect(curationPosts).toEqual([{ starred: true }]));
    const unstarBtn = await screen.findByRole("button", { name: "已收藏 · 取消" });
    expect(unstarBtn.getAttribute("aria-pressed")).toBe("true");

    // Second consecutive click -> MUST send starred = false and update UI back cleanly
    fireEvent.click(unstarBtn);
    await waitFor(() => expect(curationPosts).toEqual([{ starred: true }, { starred: false }]));
    const starBtnAfter = await screen.findByRole("button", { name: "收藏待看" });
    expect(starBtnAfter.getAttribute("aria-pressed")).toBe("false");
  }, 15_000);

  it("routes blocked YouTube auth CTA to Settings YouTube auth panel without looping to Home and provides a 1-click return link", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Content";

    const blockedItem = {
      video_id: "Y5MuBWwN8IA",
      provider: "YOUTUBE",
      work_kind: "DURABLE_CONTENT_IDENTITY",
      channel_id: "ch-blocked",
      channel_name: "Blocked Channel",
      title: null,
      source_url: "https://www.youtube.com/watch?v=Y5MuBWwN8IA",
      source_id: "src-yt-blocked",
      published_at: "2026-11-24T12:00:00Z",
      processing_status: "NEEDS_ATTENTION",
      last_error_code: "YOUTUBE_AUTH_REQUIRED",
      last_updated: "2026-11-24T12:00:00Z",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos") || input.includes("/videos?limit=200&offset=0")) {
          return okJson({
            videos: [blockedItem],
            pagination: {
              limit: 200,
              offset: 0,
              total_count: 1,
              returned_count: 1,
              has_more: false,
            },
          });
        }
        if (input.endsWith("/videos/Y5MuBWwN8IA")) {
          return okJson({
            video: blockedItem,
            captions: [],
            evidence: [],
            summary: null,
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);

    // 1. User sees the blocked item in #Content and opens its detail (or clicks auth directly)
    const viewBtn = await screen.findByRole("button", { name: "查看处理方式" });
    fireEvent.click(viewBtn);

    const authLink = await screen.findByRole("link", { name: /授权本人 YouTube 登录态/ });
    expect(authLink.getAttribute("href")).toBe(
      `#Settings/youtube-auth?return=${encodeURIComponent("#Content/Y5MuBWwN8IA")}`,
    );

    // 2. Simulating browser hash navigation when user clicks the <a href="#Settings/youtube-auth?return=...">
    location.hash = authLink.getAttribute("href")!;
    fireEvent(window, new HashChangeEvent("hashchange", { newURL: location.href }));

    // Must land on Settings -> YouTube Auth Fallback panel (NOT fall back to Home!)
    expect(
      await screen.findByRole("region", { name: "YouTube 采集登录兜底（按需）" }),
    ).toBeTruthy();

    // 3. Return CTA points back to the original blocked video
    const returnLink = await screen.findByRole("link", { name: /返回原视频继续获取/ });
    expect(returnLink.getAttribute("href")).toBe("#Content/Y5MuBWwN8IA");

    location.hash = returnLink.getAttribute("href")!;
    fireEvent(window, new HashChangeEvent("hashchange", { newURL: location.href }));
    expect(await screen.findByText(/YouTube 视频导入详情 · Y5MuBWwN8IA/)).toBeTruthy();

    // 4. Navigating to #Settings/models must also stay on Settings (never fall back to Home)
    location.hash = "#Settings/models";
    fireEvent(window, new HashChangeEvent("hashchange", { newURL: location.href }));
    expect(
      await screen.findByRole("region", { name: "YouTube 采集登录兜底（按需）" }),
    ).toBeTruthy();
  });

  it("renders blocked pending video in Content banner without duplicating it in the library list", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Content";

    const blockedItem = {
      video_id: "Y5MuBWwN8IA",
      provider: "YOUTUBE",
      work_kind: "DURABLE_CONTENT_IDENTITY",
      channel_id: "ch-blocked",
      channel_name: "Blocked Channel",
      title: null,
      source_url: "https://www.youtube.com/watch?v=Y5MuBWwN8IA",
      source_id: "src-yt-blocked",
      published_at: "2026-11-24T12:00:00Z",
      processing_status: "NEEDS_ATTENTION",
      last_error_code: "YOUTUBE_AUTH_REQUIRED",
      last_updated: "2026-11-24T12:00:00Z",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos") || input.includes("/videos?limit=200&offset=0")) {
          return okJson({
            videos: [blockedItem],
            pagination: {
              limit: 200,
              offset: 0,
              total_count: 1,
              returned_count: 1,
              has_more: false,
            },
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);

    const banner = await screen.findByRole("region", { name: "手动导入视频状态" });
    expect(within(banner).getByText(/YouTube 视频 · Y5MuBWwN8IA/)).toBeTruthy();
    expect(document.querySelectorAll(".content-media-list .content-media-row").length).toBe(0);
  });

  it("collapses Reader evidence items beyond 3 into a progressive drawer and auto-opens when targeted", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    const makeEv = (n: number) => ({
      evidence_id: `ev-${n}`,
      artifact_id: `art-${n}`,
      start_ms: n * 10000,
      end_ms: n * 10000 + 4000,
      source_language: "en",
      translation_target_language: "zh-CN",
      translated_excerpt: `第 ${n} 条译文摘录`,
      translated_language: "zh-CN",
      original_excerpt: `Excerpt number ${n}`,
      lineage_kind: "CAPTIONS",
      role: "SUPPORTING",
      created_at: "2026-11-24T12:00:00Z",
    });

    const videoPayload = {
      video: {
        video_id: "v-overflow",
        provider: "YOUTUBE",
        channel_id: "ch-1",
        channel_name: "Demo Channel",
        title: "Long Evidence Video",
        source_url: "https://www.youtube.com/watch?v=v-overflow",
        published_at: "2026-11-24T12:00:00Z",
        processing_status: "ORGANIZED",
        last_updated: "2026-11-24T12:00:00Z",
      },
      transcript: { status: "AVAILABLE", text: "Hello world" },
      note: {
        v1: { status: "UNAVAILABLE" },
        v2: { status: "AVAILABLE", summary: "Summary text", core_points: [] },
      },
      intelligence_result: { status: "NOT_PROCESSED" },
      history: [],
    };
    const evList = [makeEv(1), makeEv(2), makeEv(3), makeEv(4), makeEv(5)];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos/v-overflow/evidence")) {
          return okJson({ evidence: evList });
        }
        if (input.endsWith("/videos/v-overflow/deep-analysis")) {
          return okJson({
            deep_analysis: {
              status: {
                availability: "NOT_QUALIFIED",
                qualified: false,
                production_eligible: false,
                consent_required: false,
                routes: [],
              },
              result: null,
            },
          });
        }
        if (input.endsWith("/videos/v-overflow")) {
          return okJson(videoPayload);
        }
        return baseFetch(input, undefined, init);
      }),
    );

    location.hash = "#Content/v-overflow";
    render(<App />);

    expect(await screen.findByText(/展开其余 2 条时间轴原话片段/)).toBeTruthy();
    const drawer = document.querySelector("details.evidence-overflow-drawer") as HTMLDetailsElement;
    expect(drawer).toBeTruthy();
    expect(drawer.open).toBe(false);

    const origScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = vi.fn();
    try {
      cleanup();
      location.hash = "#Content/v-overflow/Evidence/ev-4";
      render(<App />);
      await screen.findByText(/展开其余 2 条时间轴原话片段/);
      const targetedDrawer = document.querySelector(
        "details.evidence-overflow-drawer",
      ) as HTMLDetailsElement;
      expect(targetedDrawer.open).toBe(true);
    } finally {
      Element.prototype.scrollIntoView = origScrollIntoView;
    }
  });

  it("exposes Speech and YouTube Auth jump links in Settings and keeps vault export visible when AI editor opens", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    location.hash = "#Settings";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/settings/preferences")) {
          return okJson({ active: [], history: [] });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);

    const jumpBar = await screen.findByRole("toolbar", { name: /设置分区|Settings sections/ });
    expect(within(jumpBar).getByRole("button", { name: /语音转写/ })).toBeTruthy();
    expect(within(jumpBar).getByRole("button", { name: /YouTube 授权/ })).toBeTruthy();

    fireEvent.click(await screen.findByRole("button", { name: "配置 AI 摘要与问答引擎" }));
    expect(await screen.findByRole("button", { name: "保存 AI 引擎配置" })).toBeTruthy();
    expect(
      screen.getByRole("group", { name: "知识库导出与快照" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("button", { name: "导出 Obsidian 知识库包 (.zip)" }),
    ).toBeTruthy();
  });

  it("accepts dropped local files on the LocalImport drag-and-drop dropzone", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string) => {
        if (input.endsWith("/local/native/capability")) {
          return okJson({ capability: { available: false, reason: "CLI launcher" } });
        }
        return baseFetch(input);
      }),
    );

    render(
      <UiLanguageProvider>
        <LocalImport onClose={() => {}} onSaved={() => {}} onYouTube={() => {}} />
      </UiLanguageProvider>,
    );

    const dropzone = document.querySelector("label.local-dropzone") as HTMLElement;
    expect(dropzone).toBeTruthy();
    const noteFile = new File(["# Note\nHello world"], "session-note.md", { type: "text/markdown" });
    fireEvent.dragOver(dropzone, { dataTransfer: { files: [noteFile] } });
    expect(dropzone.className).toContain("is-drag-active");
    fireEvent.drop(dropzone, { dataTransfer: { files: [noteFile] } });
    expect(await screen.findByText(/session-note\.md/)).toBeTruthy();
  });

  it("focuses Content Detail on Video Preview + Synthesis, opens auxiliary drawer on demand, and auto-opens on targeted evidence", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("yia.ui-language", "zh-CN");
    const origScrollIntoView = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = vi.fn();

    const ev1 = {
      evidence_id: "ev-1",
      artifact_id: "art-1",
      start_ms: 5000,
      end_ms: 15000,
      source_language: "en",
      translation_target_language: "zh-CN",
      translated_excerpt: "先做核心结论再按需核对原始字幕。",
      translated_language: "zh-CN",
      original_excerpt: "Lead with core synthesis and inspect raw transcript on demand.",
      lineage_kind: "CAPTIONS",
      role: "SUPPORTING",
      created_at: "2026-11-24T12:00:00Z",
    };

    const ytPayload = {
      video: {
        video_id: "vid-struct-1",
        provider: "YOUTUBE",
        channel_id: "UC1234567890123456789012",
        channel_name: "System Craft",
        title: "Product Structure Over Engineering Dump",
        source_url: "https://www.youtube.com/watch?v=vid-struct-1",
        duration_seconds: 920,
        published_at: "2026-11-24T12:00:00Z",
        processing_status: "READY",
        last_updated: "2026-11-24T12:00:00Z",
        ai_brief: {
          video_id: "vid-struct-1",
          headline_zh: "好产品应当突出视频内容与核心归纳",
          summary_zh: "主屏聚焦观看入口与提炼观点，字幕与处理记录按需抽屉查阅。",
          score: 9.2,
          score_reason_zh: "高信息密度",
          recommendation_tier: "MUST_WATCH",
          content_bucket: "DEEP_DIVE",
          is_short_noise: false,
          topics_zh: ["产品设计"],
          topic_cluster_zh: "AI 产品设计",
          core_points_json: [],
          product_opportunities_zh: ["渐进式抽屉阅读"],
          business_opportunities_zh: [],
          filtered_noise_json: [],
        },
      },
      transcript: {
        status: "AVAILABLE",
        text: "Full raw captions text.",
        timed_segments: [{ start_ms: 5000, end_ms: 15000, text: "Full raw captions text." }],
      },
      note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
      intelligence_result: { status: "NOT_PROCESSED" },
      history: [{ timestamp: "2026-11-24T12:01:00Z", status: "READY", summary: "Completed" }],
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos/vid-struct-1/evidence")) {
          return okJson({ evidence: [ev1] });
        }
        if (input.endsWith("/videos/vid-struct-1/deep-analysis")) {
          return okJson({
            deep_analysis: {
              status: { availability: "NOT_QUALIFIED", qualified: false, consent_required: false, routes: [] },
              result: null,
            },
          });
        }
        if (input.endsWith("/videos/vid-struct-1")) {
          return okJson(ytPayload);
        }
        return baseFetch(input, undefined, init);
      }),
    );

    try {
      location.hash = "#Content/vid-struct-1";
      render(<App />);

      // Video preview card and on-demand launcher bar are visible; redundant empty summary panel omitted; drawer closed
      expect(await screen.findByRole("link", { name: /在原站播放原视频/ })).toBeTruthy();
      expect(document.getElementById("section-summary")).toBeNull();
      const drawer = document.querySelector("aside.reader-ref-drawer") as HTMLElement;
      expect(drawer).toBeTruthy();
      expect(drawer.className).not.toContain("is-open");

      // Open Transcript tab via launcher card -> switch to Evidence -> Escape closes drawer
      fireEvent.click(screen.getByRole("button", { name: /查看原始字幕/ }));
      expect(drawer.className).toContain("is-open");
      expect(screen.getByRole("tab", { name: "原始字幕" }).getAttribute("aria-selected")).toBe("true");

      fireEvent.click(screen.getByRole("tab", { name: /原话证据/ }));
      expect(screen.getByRole("tab", { name: /原话证据/ }).getAttribute("aria-selected")).toBe("true");

      fireEvent.keyDown(window, { key: "Escape" });
      await waitFor(() => expect(drawer.className).not.toContain("is-open"));

      // Deep-linking directly to Evidence auto-opens the drawer to the Evidence tab
      cleanup();
      location.hash = "#Content/vid-struct-1/Evidence/ev-1";
      render(<App />);
      await screen.findByText("当前定位引用");
      const openDrawer = document.querySelector("aside.reader-ref-drawer") as HTMLElement;
      expect(openDrawer.className).toContain("is-open");
      expect(screen.getByRole("tab", { name: /原话证据/ }).getAttribute("aria-selected")).toBe("true");
    } finally {
      Element.prototype.scrollIntoView = origScrollIntoView;
    }
  });

  it("reveals an inline HTML5 <video> player pointing at /api/v1/videos/<id>/media for local videos", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content/loc-video-play";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos/loc-video-play/evidence")) return okJson({ evidence: [] });
        if (input.endsWith("/videos/loc-video-play/deep-analysis")) {
          return okJson({
            deep_analysis: {
              status: { availability: "NOT_QUALIFIED", qualified: false, consent_required: false, routes: [] },
              result: null,
            },
          });
        }
        if (input.endsWith("/videos/loc-video-play")) {
          return okJson({
            video: {
              video_id: "loc-video-play",
              provider: "LOCAL",
              media_kind: "VIDEO",
              format: "mp4",
              title: "local-demo.mp4",
              duration_seconds: 120,
              published_at: "2026-11-24T12:00:00Z",
              processing_status: "READY",
              last_updated: "2026-11-24T12:00:00Z",
            },
            transcript: { status: "NOT_PROCESSED" },
            note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
            intelligence_result: { status: "NOT_PROCESSED" },
            history: [],
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);
    const playBtn = await screen.findByRole("button", { name: "页内播放原视频" });
    fireEvent.click(playBtn);

    const videoEl = document.querySelector("video.reader-inline-player") as HTMLVideoElement;
    expect(videoEl).toBeTruthy();
    expect(videoEl.getAttribute("src")).toBe("/api/v1/videos/loc-video-play/media");
  });

  it("P1-05: enforces closed drawer inert + focus trap + Escape focus return + ARIA tabpanel keyboard navigation", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content/vid-a11y-1";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos/vid-a11y-1/evidence")) {
          return okJson({
            evidence: [
              {
                evidence_id: "ev-a1",
                artifact_id: "art-1",
                start_ms: 1000,
                end_ms: 5000,
                source_language: "zh",
                translation_target_language: "zh-CN",
                translated_excerpt: "第一条原话证据内容。",
                translated_language: "zh-CN",
                original_excerpt: "第一条原话证据内容。",
                lineage_kind: "CAPTIONS",
                role: "SUPPORTING",
                created_at: "2026-11-24T12:00:00Z",
              },
            ],
          });
        }
        if (input.endsWith("/videos/vid-a11y-1/deep-analysis")) {
          return okJson({
            deep_analysis: {
              status: { availability: "NOT_QUALIFIED", qualified: false, consent_required: false, routes: [] },
              result: null,
            },
          });
        }
        if (input.endsWith("/videos/vid-a11y-1")) {
          return okJson({
            video: {
              video_id: "vid-a11y-1",
              provider: "YOUTUBE",
              title: "Accessibility Focus Trap Demo",
              source_url: "https://www.youtube.com/watch?v=vid-a11y-1",
              duration_seconds: 300,
              published_at: "2026-11-24T12:00:00Z",
              processing_status: "READY",
              last_updated: "2026-11-24T12:00:00Z",
              ai_brief: {
                video_id: "vid-a11y-1",
                headline_zh: "抽屉无障碍焦点闭环验证",
                summary_zh: "主屏摘要正文。",
                score: 8.8,
                score_reason_zh: "高信息密度",
                recommendation_tier: "MUST_WATCH",
                content_bucket: "DEEP_DIVE",
                is_short_noise: false,
                topics_zh: ["无障碍"],
                topic_cluster_zh: "工程质量",
                core_points_json: [],
                product_opportunities_zh: [],
                business_opportunities_zh: [],
                filtered_noise_json: [],
              },
            },
            transcript: {
              status: "AVAILABLE",
              text: "Transcript body",
              timed_segments: [{ start_ms: 1000, end_ms: 5000, text: "Transcript body" }],
            },
            note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
            intelligence_result: { status: "NOT_PROCESSED" },
            history: [{ timestamp: "2026-11-24T12:01:00Z", status: "READY", summary: "Completed" }],
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);
    const transcriptLauncher = await screen.findByRole("button", { name: /查看原始字幕/ });
    const drawer = document.querySelector("aside.reader-ref-drawer") as HTMLElement & { inert: boolean };
    expect(drawer).toBeTruthy();
    expect(drawer.hasAttribute("inert")).toBe(true);
    expect(drawer.inert).toBe(true);
    expect(drawer.getAttribute("role")).toBeNull();
    // All buttons inside closed drawer must be excluded from Tab order
    for (const btn of Array.from(drawer.querySelectorAll(".reader-ref-drawer-head button"))) {
      expect(btn.getAttribute("tabindex")).toBe("-1");
    }

    // Score posture label check (TOP 2)
    expect(screen.getByText("排序分")).toBeTruthy();

    // Open drawer from launcher -> dialog semantics, active tab focus entry, Tab wrap, Arrow switching
    transcriptLauncher.focus();
    fireEvent.click(transcriptLauncher);

    await waitFor(() => expect(drawer.getAttribute("role")).toBe("dialog"));
    expect(drawer.getAttribute("aria-modal")).toBe("true");
    expect(drawer.getAttribute("aria-labelledby")).toBe("reader-ref-drawer-title");
    expect(drawer.hasAttribute("inert")).toBe(false);

    const transcriptTab = screen.getByRole("tab", { name: "原始字幕" });
    expect(document.activeElement).toBe(transcriptTab);
    expect(transcriptTab.getAttribute("aria-controls")).toBe("reader-panel-transcript");

    const tablist = screen.getByRole("tablist", { name: "辅助资料分类" });
    fireEvent.keyDown(tablist, { key: "ArrowRight" });
    const evidenceTab = screen.getByRole("tab", { name: /原话证据/ });
    expect(evidenceTab.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(evidenceTab);

    // Tab wrap inside open dialog: when focus is on close button, Tab wraps to active first control inside drawer
    const closeBtn = screen.getByRole("button", { name: /关闭 \(Esc\)/ });
    closeBtn.focus();
    fireEvent.keyDown(drawer, { key: "Tab" });
    expect(drawer.contains(document.activeElement)).toBe(true);

    // Shift+Tab from first control wraps back to last focusable control inside drawer
    evidenceTab.focus();
    fireEvent.keyDown(drawer, { key: "Tab", shiftKey: true });
    expect(drawer.contains(document.activeElement)).toBe(true);

    // Escape closes drawer, restores inert, and returns focus to trigger button
    fireEvent.keyDown(drawer, { key: "Escape" });
    await waitFor(() => expect(drawer.hasAttribute("inert")).toBe(true));
    expect(document.activeElement).toBe(transcriptLauncher);
  });

  it("P2-04: classifies HTML5 MediaError codes cleanly and supports 1-click retry", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content/loc-err-vid";

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/videos/loc-err-vid/evidence")) return okJson({ evidence: [] });
        if (input.endsWith("/videos/loc-err-vid/deep-analysis")) {
          return okJson({
            deep_analysis: {
              status: { availability: "NOT_QUALIFIED", qualified: false, consent_required: false, routes: [] },
              result: null,
            },
          });
        }
        if (input.endsWith("/videos/loc-err-vid")) {
          return okJson({
            video: {
              video_id: "loc-err-vid",
              provider: "LOCAL",
              media_kind: "VIDEO",
              format: "mp4",
              title: "codec-edge.mp4",
              duration_seconds: 95,
              published_at: "2026-11-24T12:00:00Z",
              processing_status: "READY",
              last_updated: "2026-11-24T12:00:00Z",
            },
            transcript: { status: "NOT_PROCESSED" },
            note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } },
            intelligence_result: { status: "NOT_PROCESSED" },
            history: [],
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "页内播放原视频" }));

    for (const [code, expectedTitle] of [
      [1, "媒体加载已中断"],
      [2, "本机媒体流网络传输中断"],
      [3, "浏览器解码该媒体流失败"],
      [4, "当前格式暂不支持浏览器内直接播放（或原文件已失效）"],
    ] as const) {
      const videoEl = document.querySelector("video.reader-inline-player") as HTMLVideoElement;
      expect(videoEl).toBeTruthy();
      Object.defineProperty(videoEl, "error", { configurable: true, get: () => ({ code }) });
      fireEvent.error(videoEl);
      expect(await screen.findByText(expectedTitle)).toBeTruthy();
      fireEvent.click(screen.getByRole("button", { name: "重试加载" }));
      await waitFor(() => expect(document.querySelector("video.reader-inline-player")).toBeTruthy());
    }
  });

  it("TOP 1 & P2-03: supports explicit in-place YouTube auth consent/cancel and truthful Research candidate copy", async () => {
    localStorage.setItem("intelligence.onboarding.completed.v1", "true");
    localStorage.setItem("yia.ui-language", "zh-CN");
    location.hash = "#Content/yt-auth-inline-1";

    const putPayloads: Array<Record<string, unknown>> = [];
    let checkCalls = 0;

    const blockedVideo = {
      video_id: "yt-auth-inline-1",
      provider: "YOUTUBE",
      work_kind: "DURABLE_CONTENT_IDENTITY",
      channel_id: "ch-1",
      channel_name: "Demo Channel",
      title: null,
      source_url: "https://www.youtube.com/watch?v=yt-auth-inline-1",
      source_id: "src-yt-inline-1",
      published_at: "2026-11-24T12:00:00Z",
      processing_status: "NEEDS_ATTENTION",
      last_error_code: "YOUTUBE_AUTH_REQUIRED",
      last_updated: "2026-11-24T12:00:00Z",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/youtube-auth") && init?.method === "PUT") {
          putPayloads.push(JSON.parse(String(init.body ?? "{}")) as Record<string, unknown>);
          return okJson({ enabled: true, auth_mode: "browser", browser_name: "chrome" });
        }
        if (input.endsWith("/sources/src-yt-inline-1/check") && init?.method === "POST") {
          checkCalls += 1;
          return okJson({ accepted: true });
        }
        if (input.endsWith("/videos/yt-auth-inline-1")) {
          return okJson({ video: blockedVideo, captions: [], evidence: [], summary: null });
        }
        if (input.endsWith("/research")) {
          return okJson({ research: [], total: 0 });
        }
        if (input.endsWith("/workspace-ai/settings")) {
          return okJson({ ready: true });
        }
        if (input.endsWith("/workspace-ai/research/sessions")) {
          return okJson({
            sessions: [
              {
                session_id: "qa-1",
                question: "测试跨视频回答？",
                answer_status: "GROUNDED",
                verified_citation_count: 1,
                refused: false,
                scope_label_zh: "全部候选资料",
                covered_source_count: 1,
                covered_sources: [
                  {
                    video_id: "v1",
                    title: "Video 1",
                    provider: "LOCAL",
                    channel_name: "本地",
                    locator_type: "TEXT_RANGE",
                  },
                ],
                pinned: false,
                answer_zh: "结论一句 [E1]。",
                key_takeaways_zh: [],
                action_items_zh: [],
                citations: [
                  {
                    video_id: "v1",
                    video_title: "Video 1",
                    channel_name: "本地",
                    evidence_id: "e1",
                    start_ms: null,
                    end_ms: null,
                    timestamp_label: "P1",
                    excerpt: "原文",
                    verified: true,
                  },
                ],
                obsidian_markdown: "# QA",
                provider: "ollama",
                model: "stub",
                created_at: "2026-11-24T12:00:00Z",
              },
            ],
            scope_options: {
              starred_count: 0,
              channels: [],
              topic_clusters: [],
              videos: [{ video_id: "v1", title: "Video 1", channel_name: "本地", score: 8.5 }],
            },
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(<App />);
    const inlineBtn = await screen.findByRole("button", { name: "页内授权并立即重试" });
    fireEvent.click(inlineBtn);

    const consentRegion = await screen.findByRole("region", { name: "页内 YouTube 登录态授权确认" });
    expect(within(consentRegion).getByText(/YouTube\/Google 域名白名单过滤/)).toBeTruthy();

    // Cancelling writes ZERO auth requests
    fireEvent.click(within(consentRegion).getByRole("button", { name: "取消" }));
    expect(screen.queryByRole("region", { name: "页内 YouTube 登录态授权确认" })).toBeNull();
    expect(putPayloads.length).toBe(0);
    expect(checkCalls).toBe(0);

    // Explicit consent defaults to single_video scoped grant + immediate retry POST
    fireEvent.click(inlineBtn);
    const consentRegion2 = await screen.findByRole("region", { name: "页内 YouTube 登录态授权确认" });
    fireEvent.click(within(consentRegion2).getByRole("button", { name: "确认授权并立即重试" }));
    await waitFor(() => expect(putPayloads.length).toBe(1));
    await waitFor(() => expect(checkCalls).toBe(1));
    expect(putPayloads[0]).toMatchObject({
      enabled: true,
      grant_scope: "single_video",
      target_video_id: "yt-auth-inline-1",
      auth_mode: "browser",
      browser_name: "chrome",
    });

    // Research view shows truthful candidate scope copy and verified citation/coverage pill
    cleanup();
    location.hash = "#Research";
    render(<App />);
    expect(
      await screen.findByText(/当前提问范围：候选资料 1 篇（提问时将实时核验原文）/),
    ).toBeTruthy();
    expect(await screen.findByText(/有效引用 1 条 · 覆盖来源 1 篇/)).toBeTruthy();
    expect(await screen.findByText("出处已核验")).toBeTruthy();
    expect(await screen.findByText("结论已受证据支持")).toBeTruthy();
  });

  it("P1-05 / Gate E2: ReaderReferenceDrawer excludes collapsed <details> descendants from Tab/Shift+Tab focus trap", () => {
    render(
      <ReaderReferenceDrawer
        activeTab="transcript"
        zhReader={true}
        isTextDocument={false}
        evidenceCount={0}
        historyCount={0}
        returnFocusTarget={null}
        onSelectTab={() => {}}
        onClose={() => {}}
        evidencePane={<p>无证据</p>}
        historyPane={<p>无记录</p>}
        transcriptPane={
          <div>
            <button type="button">设置本地转写</button>
            <details data-testid="diag-details">
              <summary data-testid="diag-summary">转写诊断</summary>
              <button type="button">检查可用性</button>
              <input aria-label="本地模型目录" type="text" />
            </details>
          </div>
        }
      />,
    );

    const transcriptTab = screen.getByRole("tab", { name: "原始字幕" });
    const diagSummary = screen.getByTestId("diag-summary");
    const diagDetails = screen.getByTestId("diag-details");

    // Initial focus enters the active tab; Shift+Tab must wrap to <summary>, NOT hidden controls inside closed <details>
    expect(document.activeElement).toBe(transcriptTab);
    fireEvent.keyDown(transcriptTab, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(diagSummary);

    // Forward Tab from <summary> while <details> is collapsed must wrap back to active tab
    fireEvent.keyDown(diagSummary, { key: "Tab" });
    expect(document.activeElement).toBe(transcriptTab);

    // Once <details> is opened, <summary> is no longer last focusable so Tab does not wrap back early
    diagDetails.setAttribute("open", "");
    diagSummary.focus();
    const tabNotLast = fireEvent.keyDown(diagSummary, { key: "Tab" });
    expect(tabNotLast).toBe(true);
    const hiddenInput = screen.getByLabelText("本地模型目录");
    hiddenInput.focus();
    fireEvent.keyDown(hiddenInput, { key: "Tab" });
    expect(document.activeElement).toBe(transcriptTab);
  });

  it("P1-R03 & P2-R04: splits PUT auth success vs retry check failure with revoke, guards missing sourceId & clears secrets", async () => {
    const putBodies: Array<Record<string, unknown>> = [];
    const disconnectBodies: Array<Record<string, unknown>> = [];
    let checkAttempt = 0;
    let disconnectCalls = 0;

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/youtube-auth") && init?.method === "PUT") {
          putBodies.push(JSON.parse(String(init.body ?? "{}")) as Record<string, unknown>);
          return okJson({ enabled: false, scope: "single_video" });
        }
        if (input.includes("/workspace-ai/youtube-auth") && (!init?.method || init.method === "GET")) {
          return okJson({ enabled: false, global_enabled: false, scope: "disabled", video_grant: null });
        }
        if (input.endsWith("/workspace-ai/youtube-auth/disconnect") && init?.method === "POST") {
          disconnectCalls += 1;
          disconnectBodies.push(JSON.parse(String(init.body ?? "{}")) as Record<string, unknown>);
          return okJson({ enabled: false, scope: "disabled" });
        }
        if (input.endsWith("/sources/src-a/check") && init?.method === "POST") {
          checkAttempt += 1;
          return okJson({ error: { code: "SOURCE_CHECK_FAILED", message: "retry check failed 500" } }, 500);
        }
        return okJson({});
      }),
    );

    const onRetry = vi.fn();
    const { rerender } = render(
      <InlineYouTubeAuthRecovery
        videoId="vidSplitAuth1"
        sourceId="src-a"
        zh={true}
        onAuthorizedRetry={onRetry}
      />,
    );

    // 1. P2-R04: typing cookie secret and cancelling / switching mode / changing video clears input & sends 0 requests
    fireEvent.click(screen.getByRole("button", { name: "页内授权并立即重试" }));
    fireEvent.change(screen.getByLabelText("页内授权方式"), { target: { value: "cookie_file" } });
    const textarea = screen.getByLabelText("粘贴 YouTube cookies.txt") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: ".youtube.com\tTRUE\t/\tTRUE\t0\tSID\tSECRET_TEMP" } });
    expect(textarea.value).toContain("SECRET_TEMP");

    // Cancel clears temporary cookiesText & emits zero requests
    fireEvent.click(screen.getByRole("button", { name: "取消" }));
    expect(putBodies.length).toBe(0);
    expect(checkAttempt).toBe(0);

    fireEvent.click(screen.getByRole("button", { name: "页内授权并立即重试" }));
    const textareaReopen = screen.getByLabelText("粘贴 YouTube cookies.txt") as HTMLTextAreaElement;
    expect(textareaReopen.value).toBe("");

    // Switching scope clears cookiesText too
    fireEvent.change(textareaReopen, { target: { value: "TEMP_SECRET_2" } });
    fireEvent.change(screen.getByLabelText("页内授权范围"), { target: { value: "global" } });
    expect((screen.getByLabelText("粘贴 YouTube cookies.txt") as HTMLTextAreaElement).value).toBe("");

    // 2. PUT succeeds while POST /check fails -> split state + revoke button works + double click guarded
    fireEvent.change(screen.getByLabelText("页内授权范围"), { target: { value: "single_video" } });
    fireEvent.change(screen.getByLabelText("页内授权方式"), { target: { value: "browser" } });
    const confirmBtn = screen.getByRole("button", { name: "确认授权并立即重试" });
    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn); // double-click ignored by busyRef
    await waitFor(() => expect(putBodies.length).toBe(1));
    await waitFor(() => expect(checkAttempt).toBe(1));
    expect(onRetry).not.toHaveBeenCalled();

    const alertEl = await screen.findByRole("alert");
    expect(alertEl.textContent).toContain("本次视频单次授权已写入");
    expect(alertEl.textContent).toContain("重新发起采集");

    fireEvent.click(screen.getByRole("button", { name: "撤销本次授权" }));
    await waitFor(() => expect(disconnectCalls).toBe(1));
    expect(disconnectBodies[0]).toEqual({ scope: "single_video", target_video_id: "vidSplitAuth1" });
    expect(await screen.findByText(/已撤销本页授权并清除临时 Cookie/)).toBeTruthy();

    // 3. Missing sourceId prevents confirming & prevents false retry claim
    rerender(
      <InlineYouTubeAuthRecovery
        videoId="vidNoSrc001"
        sourceId={null}
        zh={true}
        onAuthorizedRetry={onRetry}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "页内授权并立即重试" }));
    expect((screen.getByRole("button", { name: "确认授权并立即重试" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("P2-R05: ReaderReferenceDrawer marks background inert, recaptures stray focus & recovers dynamically removed focus", async () => {
    const { rerender } = render(
      <div className="app-shell">
        <div data-testid="bg-surface">
          <button type="button">背景操作按钮</button>
        </div>
        <ReaderReferenceDrawer
          activeTab="transcript"
          zhReader={true}
          isTextDocument={false}
          evidenceCount={0}
          historyCount={0}
          returnFocusTarget={null}
          onSelectTab={() => {}}
          onClose={() => {}}
          evidencePane={<p>无证据</p>}
          historyPane={<p>无记录</p>}
          transcriptPane={
            <div>
              <button type="button" data-testid="dynamic-btn">
                动态字幕操作
              </button>
            </div>
          }
        />
      </div>,
    );

    const bgSurface = screen.getByTestId("bg-surface") as HTMLElement & { inert?: boolean };
    const outsideBtn = screen.getByRole("button", { name: "背景操作按钮" });
    expect(bgSurface.hasAttribute("inert")).toBe(true);

    // Programmatic focus attempt outside modal must snap back inside the drawer
    outsideBtn.focus();
    const drawerEl = document.querySelector("aside.reader-ref-drawer") as HTMLElement;
    expect(drawerEl.contains(document.activeElement)).toBe(true);

    // Dynamic removal of the currently focused button inside open drawer recovers focus safely inside drawer
    const dynBtn = screen.getByTestId("dynamic-btn");
    dynBtn.focus();
    expect(document.activeElement).toBe(dynBtn);
    rerender(
      <div className="app-shell">
        <div data-testid="bg-surface">
          <button type="button">背景操作按钮</button>
        </div>
        <ReaderReferenceDrawer
          activeTab="transcript"
          zhReader={true}
          isTextDocument={false}
          evidenceCount={0}
          historyCount={0}
          returnFocusTarget={null}
          onSelectTab={() => {}}
          onClose={() => {}}
          evidencePane={<p>无证据</p>}
          historyPane={<p>无记录</p>}
          transcriptPane={<p>操作已完成并移除按钮</p>}
        />
      </div>,
    );
    await waitFor(() => {
      expect(drawerEl.contains(document.activeElement)).toBe(true);
    });

    // Closing drawer restores background interactivity (removes inert)
    rerender(
      <div className="app-shell">
        <div data-testid="bg-surface">
          <button type="button">背景操作按钮</button>
        </div>
        <ReaderReferenceDrawer
          activeTab={null}
          zhReader={true}
          isTextDocument={false}
          evidenceCount={0}
          historyCount={0}
          returnFocusTarget={null}
          onSelectTab={() => {}}
          onClose={() => {}}
          evidencePane={<p>无证据</p>}
          historyPane={<p>无记录</p>}
          transcriptPane={<p>已关闭</p>}
        />
      </div>,
    );
    expect(bgSurface.hasAttribute("inert")).toBe(false);
  });

  it("P1-F02 UI: YouTubeAuthSettingsPanel fixes stale circuit copy and separates global disconnect from confirmed revoke-all", async () => {
    localStorage.setItem("yia.ui-language", "zh-CN");
    const disconnectCalls: Array<Record<string, unknown>> = [];

    vi.stubGlobal(
      "fetch",
      vi.fn((input: string, init?: RequestInit) => {
        if (input.endsWith("/workspace-ai/youtube-auth") && (!init?.method || init.method === "GET")) {
          return okJson({
            enabled: true,
            global_enabled: true,
            scope: "global",
            active_single_video_grants: 2,
            auth_mode: "cookie_file",
            browser_name: "",
            supported_browsers: ["chrome", "safari"],
            cookie_configured: true,
            daily_limit: 20,
            used_today: 1,
            cooldown_seconds: 15,
            circuit_open: true,
          });
        }
        if (input.endsWith("/workspace-ai/youtube-auth/disconnect") && init?.method === "POST") {
          const parsed = JSON.parse(String(init.body ?? "{}")) as Record<string, unknown>;
          disconnectCalls.push(parsed);
          if (parsed.scope === "global") {
            return okJson({
              enabled: false,
              global_enabled: false,
              scope: "single_video",
              active_single_video_grants: 2,
              auth_mode: "disabled",
              browser_name: "",
              supported_browsers: ["chrome", "safari"],
              cookie_configured: false,
              daily_limit: 20,
              used_today: 1,
              cooldown_seconds: 15,
              circuit_open: true,
            });
          }
          return okJson({
            enabled: false,
            global_enabled: false,
            scope: "disabled",
            active_single_video_grants: 0,
            auth_mode: "disabled",
            browser_name: "",
            supported_browsers: ["chrome", "safari"],
            cookie_configured: false,
            daily_limit: 20,
            used_today: 1,
            cooldown_seconds: 15,
            circuit_open: true,
          });
        }
        return baseFetch(input, undefined, init);
      }),
    );

    render(
      <UiLanguageProvider>
        <YouTubeAuthSettingsPanel />
      </UiLanguageProvider>,
    );

    expect(await screen.findByText(/触发账号保护熔断/)).toBeTruthy();
    expect(document.body.textContent).not.toContain("重新保存设置可立即复位");
    expect(document.body.textContent).toContain("重新保存或断开不会提前解除熔断");
    expect(document.body.textContent).toContain("当前另有 2 条临时单视频授权生效中");

    // 1. Global disconnect sends scope="global" without wiping single-video grants
    fireEvent.click(screen.getByRole("button", { name: "断开全局备用授权" }));
    await waitFor(() => expect(disconnectCalls.length).toBe(1));
    expect(disconnectCalls[0]).toEqual({ scope: "global" });

    // 2. Revoke all requires explicit confirmation and sends scope="all", confirm_all=true
    fireEvent.click(screen.getByRole("button", { name: "撤销全部授权（含临时单视频）" }));
    fireEvent.click(screen.getByRole("button", { name: "确认撤销全部授权" }));
    await waitFor(() => expect(disconnectCalls.length).toBe(2));
    expect(disconnectCalls[1]).toEqual({ scope: "all", confirm_all: true });
  });
});
