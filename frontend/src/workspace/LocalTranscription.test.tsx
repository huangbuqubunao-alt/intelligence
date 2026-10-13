import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

it.each(["en", "zh-CN"])("keeps delayed transcription and diagnostics unknown without commands in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  let finish!: (value: ReturnType<typeof response>) => void;
  const fetch = vi.fn(() => new Promise<ReturnType<typeof response>>(resolve => { finish = resolve; }));
  vi.stubGlobal("fetch", fetch);
  const complete = vi.fn(), status = vi.fn();
  render(<UiLanguageProvider><LocalTranscription id="delayed" onCompleted={complete} onStatusChange={status} /></UiLanguageProvider>);
  expect(screen.getByRole("status").textContent).toBe(language === "en" ? "Reading transcription status…" : "正在读取转写状态…");
  expect(document.body.textContent).not.toMatch(/Awaiting transcription|待转写|Local model is missing|缺少本地模型/);
  for (const button of screen.getAllByRole("button")) expect((button as HTMLButtonElement).disabled).toBe(true);
  expect(status).not.toHaveBeenCalled(); expect(complete).not.toHaveBeenCalled();
  await act(async () => finish(response({ status: "READY", retry_available: false, capability })));
  await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
  expect(status).toHaveBeenCalledWith("READY"); expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(["en", "zh-CN"])("recovers failed transcription reads with only an explicit GET in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  const fetch = vi.fn().mockResolvedValueOnce({ ok: false, status: 500, json: async () => { throw new Error("private raw parse detail"); } })
    .mockResolvedValue(response({ status: "READY", retry_available: false, capability }));
  vi.stubGlobal("fetch", fetch);
  const complete = vi.fn();
  render(<UiLanguageProvider><LocalTranscription id="failed-read" onCompleted={complete} /></UiLanguageProvider>);
  const retry = await screen.findByRole("button", { name: language === "en" ? "Reload transcription status" : "重新读取转写状态" });
  expect(document.body.textContent).not.toMatch(/private raw|Awaiting transcription|待转写|Local model is missing|缺少本地模型/);
  expect(complete).not.toHaveBeenCalled();
  await userEvent.click(retry);
  await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
  expect(fetch.mock.calls).toHaveLength(2);
  expect(fetch.mock.calls.every(([path, init]) => path === "/api/v1/videos/failed-read/transcription" && (!init?.method || init.method === "GET") && init?.body === undefined)).toBe(true);
});

it("ignores a late old Content response and notifies READY once for each current Content", async () => {
  localStorage.setItem("yia.ui-language", "en");
  let finishOld!: (value: ReturnType<typeof response>) => void;
  const fetch = vi.fn((path: string) => path.includes("/old/")
    ? new Promise<ReturnType<typeof response>>(resolve => { finishOld = resolve; })
    : Promise.resolve(response({ status: "READY", retry_available: false, capability })));
  vi.stubGlobal("fetch", fetch);
  const complete = vi.fn(), status = vi.fn();
  const ui = render(<UiLanguageProvider><LocalTranscription id="old" onCompleted={complete} onStatusChange={status} /></UiLanguageProvider>);
  ui.rerender(<UiLanguageProvider><LocalTranscription id="new" onCompleted={complete} onStatusChange={status} /></UiLanguageProvider>);
  expect(screen.getByRole("status").textContent).toBe("Reading transcription status…");
  await waitFor(() => expect(complete).toHaveBeenCalledTimes(1));
  await act(async () => finishOld(response({ status: "FAILED", retry_available: true, capability })));
  expect(screen.getByRole("status").textContent).toBe("Transcription complete");
  expect(status).not.toHaveBeenCalledWith("FAILED");
  ui.rerender(<UiLanguageProvider><LocalTranscription id="third" onCompleted={complete} onStatusChange={status} /></UiLanguageProvider>);
  await waitFor(() => expect(complete).toHaveBeenCalledTimes(2));
});

it("does not present a stale running state after a polling read fails and preserves the model draft", async () => {
  localStorage.setItem("yia.ui-language", "en");
  vi.useFakeTimers();
  try {
    const fetch = vi.fn().mockResolvedValueOnce(response({ status: "RUNNING", retry_available: false, capability }))
      .mockRejectedValueOnce(new Error("read disconnected"))
      .mockResolvedValue(response({ status: "READY", retry_available: false, capability }));
    vi.stubGlobal("fetch", fetch);
    const complete = vi.fn();
    render(<UiLanguageProvider><LocalTranscription id="polling" onCompleted={complete} /></UiLanguageProvider>);
    await act(async () => {});
    expect(screen.getByRole("status").textContent).toBe("Transcribing…");
    const input = screen.getByRole("textbox") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "/already/provisioned/draft" } });
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(screen.getByRole("alert").textContent).toContain("Transcription status could not be read");
    expect(screen.queryByText("Transcribing…")).toBeNull();
    expect(input.value).toBe("/already/provisioned/draft");
    expect((screen.getByRole("button", { name: "Check availability" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Use local model" }) as HTMLButtonElement).disabled).toBe(true);
    expect(complete).not.toHaveBeenCalled();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Reload transcription status" })); });
    expect(screen.getByRole("status").textContent).toBe("Transcription complete");
    expect(complete).toHaveBeenCalledTimes(1);
    expect(input.value).toBe("/already/provisioned/draft");
    expect(fetch.mock.calls).toHaveLength(3);
    expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
  } finally { vi.useRealTimers(); }
});
