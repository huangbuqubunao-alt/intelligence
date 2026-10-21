import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { App } from "./App";

const localProvider = {
  provider: "Local", model: "qwen3:8b", scope: "SCORING_SUMMARY_ONLY",
  qualification_status: "INTELLIGENCE_UNQUALIFIED", production_eligible: false,
  adapter_available: true, authorized: false, reason: "Local Summary only.",
};
const cloudProvider = {
  provider: "moonshot", model: "kimi-k2.6", scope: "V1_VIDEO_DISTILLATION_ONLY",
  qualification_status: "QUALIFIED", production_eligible: false,
  adapter_available: true, authorized: false, credential_status: "BLOCKED", reason: "Credential unavailable.",
};
const runtime = { model: "qwen3:8b", status: "READY", installed: true, digest_valid: true };
type Language = "en" | "zh-CN";

beforeEach(() => { location.hash = "#Settings"; });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });

async function settingsView(language: Language, providers: object[] = [localProvider, cloudProvider], model = runtime) {
  localStorage.setItem("yia.ui-language", language);
  const fetch = vi.fn((path: string, _init?: RequestInit) => Promise.resolve({ ok: true, json: async () => {
    if (path.endsWith("/settings/local-intelligence")) return { local_intelligence: { status: "NOT_CONFIGURED", etag: "b".repeat(64), selected_candidate_id: null,
        actual_route: { provider: "ollama", model: "qwen3:8b", profile_id: null }, blocking_work: [],
        candidates: [{ candidate_id: "fixed-0406", model: "qwen3.5:9b-q4_K_M", runtime: "0.40.6", catalog_hash: "a".repeat(64), installation: "READY" }] } };
    if (path.endsWith("/settings")) return {
      general: { timezone: "Asia/Shanghai", output_language: "zh-CN", output_language_source: "BOOTSTRAP_DEFAULT", output_language_updated_at: null },
      providers, runtime_local_model: model,
      content_processing: { status: "READY", requires_cloud: false },
      cloud_credential: { configured: false, source: "NONE" },
    };
    if (path.endsWith("/settings/preferences")) return { active: [], history: [] };
    if (path.endsWith("/settings/source-policy")) return { policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: "BALANCED" } };
    if (path.endsWith("/settings/resource-usage")) return { usage: [] };
    if (path.endsWith("/settings/local-models")) return { connection: "REACHABLE", models: [{ model: "qwen3.5:9b-q4_K_M" }] };
    if (path.endsWith("/local/transcription/capability")) return { capability: { state: "MODEL_MISSING", runtime_available: true, model_present: false } };
    return {};
  } }));
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  const panel = (await screen.findByText(language === "en" ? "Models and processing" : "模型与处理准备")).closest("section")!;
  return { panel, fetch };
}

it.each<Language>(["en", "zh-CN"])("separates installed identity, unqualified local Intelligence and optional cloud setup (%s)", async language => {
  const { panel, fetch } = await settingsView(language);
  const copy = within(panel);
  const installedStatus = copy.getByText(language === "en" ? /qwen3:8b · Installed; identity verified/ : /qwen3:8b · 已安装，身份已核对/);
  expect(installedStatus).toBeTruthy();
  expect(installedStatus.textContent).not.toContain("qwen3.5:9b"); // Discovery does not replace the runtime identity.
  expect(copy.getByText(language === "en"
    ? "The current local model has not passed Intelligence quality verification. Existing Content, Summary and Evidence remain readable."
    : "当前本地模型尚未通过洞察质量验收。已有内容、摘要和 Evidence 仍可阅读。")).toBeTruthy();
  expect(copy.getByText(language === "en"
    ? "Installation and identity checks do not qualify a model for Intelligence."
    : "安装成功和身份核对不代表模型通过洞察资格验收。")).toBeTruthy();
  expect(copy.getByText(language === "en"
    ? "Cloud Intelligence is optional. It needs a credential and your separate authorization for each request. Content processing remains usable."
    : "云端洞察是可选方案。使用时需要配置凭据，并逐次明确授权。内容整理仍可使用。")).toBeTruthy();
  expect(copy.queryByText(/Installed and ready|已安装，可使用/)).toBeNull();
  expect(copy.getByText(language === "en" ? /Content is saved and organized locally/ : /内容将在本机保存并整理/)).toBeTruthy();
  expect(fetch.mock.calls.every(([path]) => ["/settings", "/settings/local-intelligence", "/settings/preferences", "/settings/source-policy", "/settings/resource-usage", "/settings/local-models", "/local/transcription/capability", "/backup-restore/status"].some(route => path === `/api/v1${route}`))).toBe(true);
  expect(fetch.mock.calls.every(([, init]) => (!init?.method || init.method === "GET") && init?.body === undefined)).toBe(true); // Reads never authorize or invoke work.
});

it.each<Language>(["en", "zh-CN"])("does not invent local qualification when the provider is missing or unknown (%s)", async language => {
  for (const providers of [[cloudProvider], [{ ...localProvider, qualification_status: "UNKNOWN" }, cloudProvider], [{ ...localProvider, scope: "OTHER" }, cloudProvider]]) {
    const { panel } = await settingsView(language, providers);
    expect(panel.textContent).not.toMatch(/current local model has not passed|当前本地模型尚未通过|local Intelligence is available|本地洞察可用/);
    expect(within(panel).getByText(language === "en" ? /Installation and identity checks/ : /安装成功和身份核对不代表/)).toBeTruthy();
    cleanup();
  }
});

it.each<Language>(["en", "zh-CN"])("keeps an eligible cloud model subject to separate authorization (%s)", async language => {
  const { panel } = await settingsView(language, [localProvider, { ...cloudProvider, credential_status: "AVAILABLE", production_eligible: true }]);
  expect(within(panel).getByText(language === "en"
    ? "Optional cloud analysis is available after your authorization for each request."
    : "可选云端分析已配置，每次请求仍需要你单独授权。")).toBeTruthy();
  expect(panel.textContent).toContain(language === "en" ? "current local model has not passed" : "当前本地模型尚未通过");
});

it.each(["NOT_INSTALLED", "DIGEST_MISMATCH", "UNKNOWN", "UNREACHABLE"])("keeps %s installation uncertainty visible without granting readiness", async status => {
  const { panel } = await settingsView("en", [localProvider, cloudProvider], { ...runtime, status, digest_valid: false });
  expect(within(panel).getByText(/qwen3:8b · Readiness needs attention/)).toBeTruthy();
  expect(within(panel).queryByText(/Installed; identity verified/)).toBeNull();
});

it.each<Language>(["en", "zh-CN"])("keeps cloud optional when no qualified cloud row is supplied (%s)", async language => {
  const { panel } = await settingsView(language, [localProvider]);
  expect(within(panel).getByText(language === "en"
    ? "Cloud Intelligence is optional and requires a qualified model and your separate authorization for each request. Content processing remains usable."
    : "云端洞察是可选方案，需要合格模型和逐次明确授权。内容整理仍可使用。")).toBeTruthy();
});
