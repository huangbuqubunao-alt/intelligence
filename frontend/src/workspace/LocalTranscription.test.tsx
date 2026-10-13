import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { LocalTranscription } from "./LocalTranscription";
import { UiLanguageProvider } from "./uiLanguage";
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
const capability = { state: "READY", runtime_detected: true, runtime_available: true, model_present: true, executor_compatible: true, executor: "fixture", execution_identity: "selected-identity", model_identity: "sha256:fixture" };
const response = (transcription: object) => ({ ok: true, json: async () => ({ transcription }) });
it.each(["en", "zh-CN"])("distinguishes acoustic qualification from installed assets in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  const labels = language === "en" ? ["Not tested", "Qualification running…", "Qualification passed", "Acoustic qualification failed", "Qualification stale"] : ["尚未测试", "正在进行资格验证…", "资格验证通过", "资格验证失败", "资格验证已失效"];
  for (const [index, state] of ["NOT_TESTED", "RUNNING", "PASSED", "FAILED", "STALE"].entries()) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ status: "QUALIFICATION_REQUIRED", retry_available: false, capability: { ...capability, qualification_state: state, production_eligible: state === "PASSED" } })));
    const ui = render(<UiLanguageProvider><LocalTranscription id={`local-${state}`} onCompleted={() => {}} /></UiLanguageProvider>);
    await screen.findByText(labels[index]);
    expect(document.body.textContent).toContain(language === "en" ? "Acoustic qualification" : "语音转写资格");
    expect(screen.queryByRole("button", { name: language === "en" ? "Start transcription" : "开始转写" })).toBeNull();
    ui.unmount();
  }
});
it.each(["en", "zh-CN"])("localizes missing model and diagnostics in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  const fetch = vi.fn().mockResolvedValue(response({ status: "MODEL_MISSING", retry_available: false, capability: { ...capability, state: "MODEL_MISSING", model_present: false, reason_code: "MODEL_MISSING" } }));
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalTranscription id="local-id" onCompleted={() => {}} /></UiLanguageProvider>);
  await screen.findByText(language === "en" ? "Local model is missing" : "缺少本地模型", { selector: "p" });
  expect(screen.queryByRole("button", { name: language === "en" ? "Start transcription" : "开始转写" })).toBeNull();
  expect(document.body.textContent).not.toContain("MODEL_MISSING");
});
it("starts the visible identity and prevents duplicate clicks", async () => {
  localStorage.setItem("yia.ui-language", "en");
  let started = false;
  const fetch = vi.fn((path: string, init?: RequestInit) => {
    if (init?.method === "POST") { started = true; return new Promise(() => {}); }
    return Promise.resolve(response({ status: "PENDING", start_available: true, retry_available: false, capability }));
  });
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalTranscription id="local-id" onCompleted={() => {}} /></UiLanguageProvider>);
  const button = await screen.findByRole("button", { name: "Start transcription" });
  await userEvent.dblClick(button);
  expect(started).toBe(true);
  expect(fetch.mock.calls.filter(call => call[1]?.method === "POST")).toHaveLength(1);
  expect(fetch.mock.calls.find(call => call[1]?.method === "POST")?.[1]?.body).toBe(JSON.stringify({ execution_identity: "selected-identity" }));
});
it("localizes retry errors by code without displaying private raw messages", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  const fetch = vi.fn((_path: string, init?: RequestInit) => Promise.resolve(init?.method === "POST" ? { ok: false, json: async () => ({ error: { code: "EXECUTOR_IDENTITY_CHANGED", message: "/Users/private/raw exception" } }) } : response({ status: "FAILED", retry_available: true, capability, last_failure_category: "EXECUTOR_TIMEOUT" })));
  vi.stubGlobal("fetch", fetch);
  render(<UiLanguageProvider><LocalTranscription id="local-id" onCompleted={() => {}} /></UiLanguageProvider>);
  await userEvent.click(await screen.findByRole("button", { name: "重试转写" }));
  await screen.findByRole("alert");
  expect(screen.getByRole("alert").textContent).toContain("所选执行器或模型已变化");
  expect(document.body.textContent).not.toContain("/Users/");
});
it("refreshes Content exactly once after trusted completion", async () => {
  localStorage.setItem("yia.ui-language", "en");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ status: "READY", retry_available: false, capability })));
  const complete = vi.fn();
  const status = vi.fn();
  const ui = render(<UiLanguageProvider><LocalTranscription id="local-id" onStatusChange={status} onCompleted={complete} /></UiLanguageProvider>);
  await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
  expect(status).toHaveBeenCalledWith("READY");
  ui.rerender(<UiLanguageProvider><LocalTranscription id="local-id" onCompleted={complete} /></UiLanguageProvider>);
  expect(complete).toHaveBeenCalledTimes(1);
});

it.each(["en", "zh-CN"])("explains invalid transcription without claiming a decoder ran in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  const fetch = vi.fn().mockResolvedValue(response({ status: "FAILED", retry_available: true, last_failure_category: "TRANSCRIPT_INVALID", capability: { ...capability, qualification_state: "PASSED", production_eligible: true } }));
  vi.stubGlobal("fetch", fetch);
  const complete = vi.fn();
  const status = vi.fn();
  render(<UiLanguageProvider><LocalTranscription id="local-noise" onCompleted={complete} onStatusChange={status} /></UiLanguageProvider>);
  await screen.findByText(language === "en" ? "No usable transcript was accepted. Your original file is saved. Check for clear speech before retrying transcription." : "未获得可用字幕，原文件已保留。请确认录音包含清晰语音后，再重试转写。");
  expect(screen.getByText(language === "en" ? "Local transcription failed" : "本地转写失败", { selector: "p[role=status]" })).toBeTruthy();
  expect(screen.getByRole("button", { name: language === "en" ? "Retry transcription" : "重试转写" })).toBeTruthy();
  expect(document.body.textContent).not.toContain(language === "en" ? "executor returned" : "执行器返回");
  expect(status).toHaveBeenCalledWith("FAILED");
  expect(complete).not.toHaveBeenCalled();
  expect(fetch.mock.calls).toHaveLength(1);
});
