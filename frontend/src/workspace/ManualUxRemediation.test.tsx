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
    expect(authCta.getAttribute("href")).toBe("#Settings/youtube-auth");
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

    fireEvent.click(screen.getByRole("button", { name: "一键断开并清除" }));
    await waitFor(() => expect(disconnected).toBe(true));
    expect(await screen.findByText(/未启用（仅免登录直采/)).toBeTruthy();
  });
});
