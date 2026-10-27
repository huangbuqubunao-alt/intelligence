import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ModelSettings } from "./ModelSettings";
import { UiLanguageProvider } from "./uiLanguage";

const candidate = { provider: "zhipu_bigmodel", model: "glm-4.7-flash", qualification: "NOT_VERIFIED", budget: "CLOSED" };
function setup(language = "en") {
  history.replaceState(null, "", "#Settings");
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
  const view = render(<UiLanguageProvider><details open><summary>Outer Cloud setup</summary><ModelSettings
    credential={{ configured: true, source: "KEYCHAIN" }} onSaved={vi.fn()} message="" setMessage={vi.fn()} /></details></UiLanguageProvider>);
  return { ...view, stores, calls, fetch };
}
const newToggle = () => screen.getByText("BigModel GLM-4.7-Flash candidate setup");
const oldToggle = () => screen.getByText("Moonshot / kimi-k2.6 credential setup");
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
  fireEvent.click(screen.getByText(language === "en" ? "Moonshot / kimi-k2.6 credential setup" : "Moonshot / kimi-k2.6 密钥设置"));
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
