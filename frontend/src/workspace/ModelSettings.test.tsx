import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ModelSettings } from "./ModelSettings";
import { UiLanguageProvider } from "./uiLanguage";

const candidate = { provider: "zhipu_bigmodel", model: "glm-4.7-flash", qualification: "NOT_VERIFIED", budget: "CLOSED" };
function setup(language = "en", hash = "#Settings", outerOpen = true) {
  history.replaceState(null, "", hash);
  localStorage.setItem("yia.ui-language", language);
  const stores = { big: "synthetic-saved-big", old: "synthetic-saved-moonshot" };
  const calls: { path: string; method: string }[] = [];
  const fetch = vi.fn(async (path: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    calls.push({ path, method });
    if (path.endsWith("local-models")) return { ok: true, json: async () => ({ connection: "REACHABLE", models: [] }) };
    const isNew = path.includes("bigmodel-credential");
    if (method === "PUT") stores[isNew ? "big" : "old"] = JSON.parse(String(init?.body)).credential;
    if (method === "POST") stores[isNew ? "big" : "old"] = "";
    const value = stores[isNew ? "big" : "old"];
    return { ok: true, json: async () => ({ ...(isNew ? candidate : {}), configured: !!value, source: value ? "KEYCHAIN" : "NONE" }) };
  });
  vi.stubGlobal("fetch", fetch);
  const view = render(<UiLanguageProvider><details open={outerOpen}><summary>Outer Cloud setup</summary><ModelSettings
    credential={{ configured: true, source: "KEYCHAIN" }} onSaved={vi.fn()} message="" setMessage={vi.fn()} /></details></UiLanguageProvider>);
  return { ...view, stores, calls, fetch };
}
const newToggle = () => screen.getByText("BigModel GLM-4.7-Flash candidate setup");
const oldToggle = () => screen.getByText("Kimi / Moonshot API credential setup");
const passwords = () => document.querySelectorAll('input[type="password"]');

test("only an explicitly selected service mounts a password; switching never transfers drafts or changes saved keys", async () => {
  const { stores, calls } = setup();
  expect(passwords()).toHaveLength(0);
  fireEvent.click(newToggle());
  const newInput = await screen.findByLabelText("BigModel API key") as HTMLInputElement;
  await screen.findByLabelText("Confirm BigModel key deletion");
  fireEvent.change(newInput, { target: { value: "synthetic-new-draft" } });
  fireEvent.click(screen.getByLabelText("Confirm BigModel key deletion"));
  fireEvent.click(oldToggle());
  const oldInput = await screen.findByLabelText("Moonshot API key") as HTMLInputElement;
  expect(passwords()).toHaveLength(1);
  expect(screen.queryByLabelText("BigModel API key")).toBeNull();
  expect(oldInput.value).toBe("");
  fireEvent.change(oldInput, { target: { value: "synthetic-old-draft" } });
  fireEvent.click(screen.getByLabelText("Confirm Moonshot key deletion"));
  fireEvent.click(newToggle());
  await screen.findByLabelText("BigModel API key");
  expect((screen.getByLabelText("BigModel API key") as HTMLInputElement).value).toBe("");
  await waitFor(() => expect((screen.getByLabelText("Confirm BigModel key deletion") as HTMLInputElement).checked).toBe(false));
  expect(passwords()).toHaveLength(1);
  expect(stores).toEqual({ big: "synthetic-saved-big", old: "synthetic-saved-moonshot" });
  expect(calls.filter(call => call.method !== "GET")).toEqual([]);
});

test.each(["bigmodel", "moonshot"])("outer fold unmounts all secret inputs and clears %s confirmation", async service => {
  const { stores } = setup();
  fireEvent.click(service === "bigmodel" ? newToggle() : oldToggle());
  const label = service === "bigmodel" ? "BigModel API key" : "Moonshot API key";
  const confirm = service === "bigmodel" ? "Confirm BigModel key deletion" : "Confirm Moonshot key deletion";
  fireEvent.change(await screen.findByLabelText(label), { target: { value: "synthetic-hidden-draft" } });
  fireEvent.click(await screen.findByLabelText(confirm));
  fireEvent.click(screen.getByText("Outer Cloud setup"));
  await waitFor(() => expect(passwords()).toHaveLength(0));
  fireEvent.click(screen.getByText("Outer Cloud setup"));
  expect(passwords()).toHaveLength(0);
  fireEvent.click(service === "bigmodel" ? newToggle() : oldToggle());
  expect((await screen.findByLabelText(label) as HTMLInputElement).value).toBe("");
  expect((await screen.findByLabelText(confirm) as HTMLInputElement).checked).toBe(false);
  expect(stores).toEqual({ big: "synthetic-saved-big", old: "synthetic-saved-moonshot" });
});

test("switch away and back during a save neither repeats it nor revives drafts; read selected store after settlement", async () => {
  const { fetch, calls, stores } = setup();
  fireEvent.click(newToggle());
  fireEvent.change(await screen.findByLabelText("BigModel API key"), { target: { value: "synthetic-inflight-new" } });
  await screen.findByLabelText("Confirm BigModel key deletion");
  let finish!: () => void;
  fetch.mockImplementationOnce(async (path, init) => {
    calls.push({ path, method: init?.method ?? "GET" });
    await new Promise<void>(resolve => { finish = resolve; });
    stores.big = "synthetic-inflight-new";
    return { ok: true, json: async () => ({ ...candidate, configured: true, source: "KEYCHAIN" }) };
  });
  const save = screen.getByRole("button", { name: "Save BigModel key securely" });
  fireEvent.click(save); fireEvent.click(save);
  fireEvent.click(oldToggle());
  await screen.findByLabelText("Moonshot API key");
  fireEvent.click(newToggle());
  const returned = await screen.findByLabelText("BigModel API key") as HTMLInputElement;
  expect(returned.value).toBe("");
  expect(returned.disabled).toBe(true);
  await act(async () => finish());
  await waitFor(() => expect(calls.filter(c => c.path.endsWith("bigmodel-credential") && c.method === "GET")).toHaveLength(2));
  expect(calls.filter(c => c.method === "PUT")).toEqual([{ path: "/api/v1/settings/bigmodel-credential", method: "PUT" }]);
  expect(returned.value).toBe("");
  expect(stores.old).toBe("synthetic-saved-moonshot");
});

test.each(["en", "zh-CN"])("legacy editor still saves/deletes only Moonshot with service-specific controls (%s)", async language => {
  const { stores, calls } = setup(language);
  fireEvent.click(screen.getByText(language === "en" ? "Kimi / Moonshot API credential setup" : "Kimi / Moonshot API 密钥设置"));
  const input = await screen.findByLabelText(language === "en" ? "Moonshot API key" : "Moonshot API 密钥");
  fireEvent.change(input, { target: { value: "synthetic-old-save" } });
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Save Moonshot key securely" : "安全保存 Moonshot 密钥" }));
  await waitFor(() => expect((input as HTMLInputElement).value).toBe(""));
  fireEvent.click(screen.getByLabelText(language === "en" ? "Confirm Moonshot key deletion" : "确认删除 Moonshot 密钥"));
  fireEvent.click(screen.getByRole("button", { name: language === "en" ? "Delete Moonshot key" : "删除 Moonshot 密钥" }));
  await waitFor(() => expect(stores.old).toBe(""));
  expect(stores.big).toBe("synthetic-saved-big");
  expect(calls.filter(c => c.method !== "GET")).toEqual([{ path: "/api/v1/settings/cloud-credential", method: "PUT" }, { path: "/api/v1/settings/cloud-credential/delete", method: "POST" }]);
});

test("legacy save stays once-only across provider switches and cannot repopulate either draft", async () => {
  const { fetch, calls, stores } = setup();
  fireEvent.click(oldToggle());
  fireEvent.change(await screen.findByLabelText("Moonshot API key"), { target: { value: "synthetic-old-inflight" } });
  let finish!: () => void;
  fetch.mockImplementationOnce(async (path, init) => {
    calls.push({ path, method: init?.method ?? "GET" });
    await new Promise<void>(resolve => { finish = resolve; });
    stores.old = "synthetic-old-inflight";
    return { ok: true, json: async () => ({ configured: true, source: "KEYCHAIN" }) };
  });
  const save = screen.getByRole("button", { name: "Save Moonshot key securely" });
  fireEvent.click(save); fireEvent.click(save);
  fireEvent.click(newToggle());
  expect((await screen.findByLabelText("BigModel API key") as HTMLInputElement).value).toBe("");
  expect(passwords()).toHaveLength(1);
  fireEvent.click(oldToggle());
  const returned = await screen.findByLabelText("Moonshot API key") as HTMLInputElement;
  expect(returned.value).toBe(""); expect(returned.disabled).toBe(true);
  await act(async () => finish());
  await waitFor(() => expect(returned.disabled).toBe(false));
  expect(returned.value).toBe("");
  expect(calls.filter(c => c.method === "PUT")).toEqual([{ path: "/api/v1/settings/cloud-credential", method: "PUT" }]);
  expect(stores.big).toBe("synthetic-saved-big");
});

test("returning to BigModel reads current saved metadata without copying either saved key into a field", async () => {
  const { stores, calls } = setup();
  fireEvent.click(newToggle());
  await screen.findByLabelText("Confirm BigModel key deletion");
  fireEvent.click(oldToggle());
  await screen.findByLabelText("Moonshot API key");
  stores.big = "";
  fireEvent.click(newToggle());
  await screen.findByText("Not configured");
  expect(screen.queryByLabelText("Confirm BigModel key deletion")).toBeNull();
  expect((screen.getByLabelText("BigModel API key") as HTMLInputElement).value).toBe("");
  expect(calls.filter(c => c.path.endsWith("bigmodel-credential"))).toHaveLength(2);
  expect(calls.filter(c => c.method !== "GET")).toEqual([]);
});

test("unmount during save keeps the dispatched write, with no replay or hidden editor after late response", async () => {
  const { fetch, calls, stores, unmount } = setup();
  fireEvent.click(newToggle());
  await screen.findByLabelText("Confirm BigModel key deletion");
  fireEvent.change(screen.getByLabelText("BigModel API key"), { target: { value: "synthetic-unmount-save" } });
  let finish!: () => void;
  fetch.mockImplementationOnce(async (path, init) => {
    calls.push({ path, method: init?.method ?? "GET" });
    await new Promise<void>(resolve => { finish = resolve; });
    stores.big = "synthetic-unmount-save";
    return { ok: true, json: async () => ({ ...candidate, configured: true, source: "KEYCHAIN" }) };
  });
  fireEvent.click(screen.getByRole("button", { name: "Save BigModel key securely" }));
  unmount();
  await act(async () => finish());
  expect(passwords()).toHaveLength(0);
  expect(calls.filter(c => c.method !== "GET")).toEqual([{ path: "/api/v1/settings/bigmodel-credential", method: "PUT" }]);
  expect(stores.old).toBe("synthetic-saved-moonshot");
  expect(stores.big).toBe("synthetic-unmount-save");
});

test.each(["en", "zh-CN"])("Kimi provider direct link opens only its editor and retains safe Content return (%s)", async language => {
  const { container, calls, stores } = setup(language, "#Settings/models/moonshot?return=%23Content%2Fvideo-1%2FEvidence%2Fevidence-1", false);
  expect(await screen.findByLabelText(language === "en" ? "Moonshot API key" : "Moonshot API 密钥")).toBeTruthy();
  expect(screen.getByText(language === "en" ? "Kimi / Moonshot API credential setup" : "Kimi / Moonshot API 密钥设置")).toBeTruthy();
  expect(container.querySelectorAll("details[open]")).toHaveLength(2);
  expect(document.activeElement?.id).toBe("moonshot-settings");
  expect(passwords()).toHaveLength(1);
  expect(screen.queryByLabelText(language === "en" ? "BigModel API key" : "智谱 API 密钥")).toBeNull();
  expect(container.textContent).not.toContain("kimi-k2.6");
  expect(screen.getByText(language === "en" ? "Public YouTube Content only" : "仅限公开 YouTube 内容")).toBeTruthy();
  expect(screen.getByRole("link", { name: language === "en" ? "Back to Content" : "返回内容" }).getAttribute("href")).toBe("#Content/video-1/Evidence/evidence-1");
  expect(calls.filter(call => call.method !== "GET")).toEqual([]);
  expect(stores).toEqual({ big: "synthetic-saved-big", old: "synthetic-saved-moonshot" });
});

test.each(["https://evil.example", "javascript:alert(1)", "#Settings", "#Content/video-1#Settings", "#Content/video-\u0000"])("Kimi return refuses non-Content or control target %s", async target => {
  setup("en", `#Settings/models/moonshot?return=${encodeURIComponent(target)}`);
  await screen.findByLabelText("Moonshot API key");
  expect(screen.queryByRole("link", { name: "Back to Content" })).toBeNull();
});

test("Kimi hash navigation clears both drafts and deletion confirmations without saving", async () => {
  const { calls, stores } = setup();
  fireEvent.click(newToggle());
  fireEvent.change(await screen.findByLabelText("BigModel API key"), { target: { value: "synthetic-big-deep-draft" } });
  fireEvent.click(await screen.findByLabelText("Confirm BigModel key deletion"));
  await act(async () => { location.hash = "#Settings/models/moonshot"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
  const moonshot = await screen.findByLabelText("Moonshot API key") as HTMLInputElement;
  expect(moonshot.value).toBe("");
  expect(passwords()).toHaveLength(1);
  fireEvent.change(moonshot, { target: { value: "synthetic-kimi-deep-draft" } });
  fireEvent.click(screen.getByLabelText("Confirm Moonshot key deletion"));
  await act(async () => { location.hash = "#Settings/models/bigmodel"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
  expect((await screen.findByLabelText("BigModel API key") as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("Confirm BigModel key deletion") as HTMLInputElement).checked).toBe(false);
  await act(async () => { location.hash = "#Settings/models/moonshot"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
  expect((await screen.findByLabelText("Moonshot API key") as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("Confirm Moonshot key deletion") as HTMLInputElement).checked).toBe(false);
  await act(async () => { location.hash = "#Content/video-1"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
  expect(passwords()).toHaveLength(0);
  expect(calls.filter(call => call.method !== "GET")).toEqual([]);
  expect(stores).toEqual({ big: "synthetic-saved-big", old: "synthetic-saved-moonshot" });
});

test("Kimi direct entry opens every ancestor and folding an outer ancestor discards the draft", async () => {
  history.replaceState(null, "", "#Settings/models/moonshot");
  localStorage.setItem("yia.ui-language", "en");
  const fetch = vi.fn(async (_path: string, _init?: RequestInit) => ({ ok: true, json: async () => ({ configured: true, source: "KEYCHAIN" }) }));
  vi.stubGlobal("fetch", fetch);
  const { container } = render(<UiLanguageProvider><details><summary>Advanced outer</summary>
    <details><summary>Cloud inner</summary><ModelSettings credential={{ configured: true, source: "KEYCHAIN" }}
      onSaved={vi.fn()} message="" setMessage={vi.fn()} /></details></details></UiLanguageProvider>);
  const input = await screen.findByLabelText("Moonshot API key");
  expect(container.querySelectorAll("details[open]")).toHaveLength(3);
  fireEvent.change(input, { target: { value: "synthetic-outer-draft" } });
  fireEvent.click(screen.getByLabelText("Confirm Moonshot key deletion"));
  fireEvent.click(screen.getByText("Advanced outer"));
  await waitFor(() => expect(passwords()).toHaveLength(0));
  fireEvent.click(screen.getByText("Advanced outer"));
  expect(passwords()).toHaveLength(0);
  fireEvent.click(screen.getByText("Kimi / Moonshot API credential setup"));
  expect((await screen.findByLabelText("Moonshot API key") as HTMLInputElement).value).toBe("");
  expect((screen.getByLabelText("Confirm Moonshot key deletion") as HTMLInputElement).checked).toBe(false);
  expect(fetch.mock.calls.every(([, init]) => (init?.method ?? "GET") === "GET")).toBe(true);
});
