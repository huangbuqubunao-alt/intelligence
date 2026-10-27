import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BigModelSettings } from "./BigModelSettings";
import { UiLanguageProvider } from "./uiLanguage";

const empty = { provider: "zhipu_bigmodel", model: "glm-4.7-flash", configured: false, source: "NONE", qualification: "NOT_VERIFIED", budget: "CLOSED" };
const reply = (data: object) => Promise.resolve({ ok: true, json: async () => data });
function setup(language = "en") {
  localStorage.setItem("yia.ui-language", language);
  const calls: { path: string; method: string; body?: string }[] = [];
  const fetch = vi.fn((path: string, init?: RequestInit) => {
    calls.push({ path, method: init?.method ?? "GET", body: init?.body as string | undefined });
    return reply(init?.method === "PUT" ? { ...empty, configured: true, source: "KEYCHAIN" } : empty);
  });
  vi.stubGlobal("fetch", fetch);
  return { calls, fetch };
}

test.each(["en", "zh-CN"])("finite candidate saves config only, clears password, keeps honest status (%s)", async language => {
  const { calls } = setup(language);
  render(<UiLanguageProvider><BigModelSettings /></UiLanguageProvider>);
  fireEvent.click(screen.getByText(language === "en" ? "BigModel GLM-4.7-Flash candidate setup" : "智谱 GLM-4.7-Flash 候选设置"));
  const input = await screen.findByLabelText(language === "en" ? "BigModel API key" : "智谱 API 密钥");
  await waitFor(() => expect(calls).toHaveLength(1));
  fireEvent.change(input, { target: { value: "synthetic-ui-only" } });
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Save BigModel key securely" : "安全保存智谱密钥" }));
  await screen.findByText(language === "en" ? "BigModel key saved. No model was run; quality and account eligibility remain unverified." : "智谱密钥已保存，未运行模型；质量与账号权益仍未验证。");
  expect((input as HTMLInputElement).value).toBe("");
  expect(calls.map(c => [c.path, c.method])).toEqual([["/api/v1/settings/bigmodel-credential", "GET"], ["/api/v1/settings/bigmodel-credential", "PUT"]]);
  expect(JSON.stringify(localStorage)).not.toContain("synthetic-ui-only");
  expect(screen.queryByText("synthetic-ui-only")).toBeNull();
  expect(screen.getByText(language === "en" ? "Quality not verified · Execution closed" : "质量未验证 · 执行未开放")).toBeTruthy();
});

test("failure is redacted, draft retained for explicit retry; selection/navigation clears it", async () => {
  const { fetch } = setup();
  render(<UiLanguageProvider><BigModelSettings /></UiLanguageProvider>);
  fireEvent.click(screen.getByText("BigModel GLM-4.7-Flash candidate setup"));
  const input = await screen.findByLabelText("BigModel API key");
  await screen.findByText("Not configured");
  fireEvent.change(input, { target: { value: "synthetic-ui-only" } });
  fetch.mockImplementationOnce(() => Promise.reject(new Error("synthetic-ui-only native secret")));
  fireEvent.click(screen.getByRole("button", { name: "Save BigModel key securely" }));
  expect((await screen.findByRole("alert")).textContent).not.toContain("synthetic-ui-only");
  expect((input as HTMLInputElement).value).toBe("synthetic-ui-only");
  await act(async () => { location.hash = "#Content/video-1/Evidence/evidence-1"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
  expect((input as HTMLInputElement).value).toBe("");
});

test("direct link expands and focuses candidate, returns to exact Content Evidence", async () => {
  setup();
  location.hash = "#Settings/models/bigmodel?return=%23Content%2Fvideo-1%2FEvidence%2Fevidence-1";
  const { container } = render(<UiLanguageProvider><details><summary>Cloud</summary><BigModelSettings /></details></UiLanguageProvider>);
  await screen.findByText("Not configured");
  expect(container.querySelectorAll("details[open]")).toHaveLength(2);
  expect(document.activeElement?.id).toBe("bigmodel-settings");
  expect(screen.getByRole("link", { name: "Back to Content" }).getAttribute("href")).toBe("#Content/video-1/Evidence/evidence-1");
});

test("malformed status stays closed, explicit read retry; untrusted return ignored", async () => {
  const { fetch } = setup();
  fetch.mockImplementationOnce(() => reply({ ...empty, qualification: "PASSED" }));
  location.hash = "#Settings/models/bigmodel?return=https%3A%2F%2Fevil.example";
  render(<UiLanguageProvider><BigModelSettings /></UiLanguageProvider>);
  fireEvent.click(screen.getByText("BigModel GLM-4.7-Flash candidate setup"));
  await screen.findByRole("alert");
  expect(screen.queryByRole("link", { name: "Back to Content" })).toBeNull();
  expect((screen.getByRole("button", { name: "Save BigModel key securely" }) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Read BigModel key status" }));
  await screen.findByText("Not configured");
});


test("closed candidate is lazy; a double submit writes once and deletion stays provider-specific", async () => {
  const { calls, fetch } = setup();
  location.hash = "#Settings";
  render(<UiLanguageProvider><BigModelSettings /></UiLanguageProvider>);
  expect(calls).toEqual([]);
  fireEvent.click(screen.getByText("BigModel GLM-4.7-Flash candidate setup"));
  await screen.findByText("Not configured");
  const input = screen.getByLabelText("BigModel API key") as HTMLInputElement;
  fireEvent.change(input, { target: { value: "synthetic-double-submit" } });
  let finish!: (value: { ok: boolean; json: () => Promise<object> }) => void;
  fetch.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  const save = screen.getByRole("button", { name: "Save BigModel key securely" });
  fireEvent.click(save); fireEvent.click(save);
  expect(fetch).toHaveBeenCalledTimes(2);
  await act(async () => finish({ ok: true, json: async () => ({ ...empty, configured: true, source: "KEYCHAIN" }) }));
  await screen.findByText("Configured in macOS Keychain");
  expect(input.value).toBe("");
  const deletion = screen.getByRole("button", { name: "Delete BigModel key" }) as HTMLButtonElement;
  expect(deletion.disabled).toBe(true);
  fireEvent.click(screen.getByLabelText("Confirm BigModel key deletion"));
  fireEvent.click(deletion);
  await screen.findByText("BigModel key deleted. Other providers and existing Content are unchanged.");
  expect(calls.at(-1)).toEqual({ path: "/api/v1/settings/bigmodel-credential/delete", method: "POST", body: '{"confirm":"DELETE"}' });
  expect(screen.queryByLabelText("Confirm BigModel key deletion")).toBeNull();
});

test("collapsing the provider clears its draft and reopening makes no duplicate request", async () => {
  const { fetch } = setup();
  location.hash = "#Settings";
  render(<UiLanguageProvider><BigModelSettings /></UiLanguageProvider>);
  const toggle = screen.getByText("BigModel GLM-4.7-Flash candidate setup");
  fireEvent.click(toggle);
  await screen.findByText("Not configured");
  const input = screen.getByLabelText("BigModel API key") as HTMLInputElement;
  fireEvent.change(input, { target: { value: "synthetic-collapsed" } });
  fireEvent.click(toggle);
  await waitFor(() => expect(input.value).toBe(""));
  fireEvent.click(toggle);
  expect(fetch).toHaveBeenCalledOnce();
});

test("save receipt with unconfirmed key state never reports saved", async () => {
  const { fetch } = setup();
  location.hash = "#Settings";
  render(<UiLanguageProvider><BigModelSettings /></UiLanguageProvider>);
  fireEvent.click(screen.getByText("BigModel GLM-4.7-Flash candidate setup"));
  await screen.findByText("Not configured");
  fireEvent.change(screen.getByLabelText("BigModel API key"), { target: { value: "synthetic-unknown-save" } });
  fetch.mockImplementationOnce(() => reply({ ...empty, source: "UNAVAILABLE" }));
  fireEvent.click(screen.getByRole("button", { name: "Save BigModel key securely" }));
  await screen.findByRole("alert");
  expect(screen.queryByText("BigModel key saved. No model was run; quality and account eligibility remain unverified.")).toBeNull();
});
