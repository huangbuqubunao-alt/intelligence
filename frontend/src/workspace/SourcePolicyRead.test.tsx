import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ExistingSourceForm } from "./App";
import { UiLanguageProvider } from "./uiLanguage";
const policy = { source_policy_revision_id: null, initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: ["robotics"], ignore_rules: ["sponsored"], distillation_style: "BALANCED" };
const response = (value: unknown) => ({ ok: true, status: 200, json: async () => value });
const source = { source_id: "source-1", canonical_url: "https://www.youtube.com/watch?v=abc", enabled: true, processing_policy: "STANDARD_INTELLIGENCE", display_name: "A video", last_error: null };
function form(modes: NonNullable<Parameters<typeof ExistingSourceForm>[0]["policyModes"]> = { focus: "INHERIT", ignore: "INHERIT", style: "INHERIT" }) { return render(<UiLanguageProvider><ExistingSourceForm source={source} policy={policy} policyModes={modes} onClose={vi.fn()} onSaved={vi.fn()} /></UiLanguageProvider>); }
function save() { return screen.getByRole("button", { name: "Save changes" }) as HTMLButtonElement; }
beforeEach(() => localStorage.setItem("yia.ui-language", "en"));
afterEach(() => vi.unstubAllGlobals());
it("shows pending policy as loading, keeps drafts editable, and blocks inherited save", async () => {
  let resolve!: (value: ReturnType<typeof response>) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise(r => { resolve = r; })));
  form();
  expect(screen.getByRole("status").textContent).toContain("Loading global interests");
  expect(screen.queryByText(/Not set/)).toBeNull();
  expect(save().disabled).toBe(true);
  fireEvent.change(screen.getByLabelText("Source URL"), { target: { value: "https://www.youtube.com/watch?v=draft" } });
  await act(async () => resolve(response({ policy })));
  await screen.findByText("Global focus: robotics");
  expect(save().disabled).toBe(false);
  expect((screen.getByLabelText("Source URL") as HTMLInputElement).value).toContain("draft");
});
it.each([
  ["transport", () => Promise.reject(new TypeError("Failed to fetch"))],
  ["service", () => Promise.resolve({ ok: false, status: 503, json: async () => { throw new SyntaxError("HTML"); } })],
  ["unparseable", () => Promise.resolve({ ok: true, status: 200, json: async () => { throw new SyntaxError("empty"); } })],
  ["empty object", () => Promise.resolve(response({}))],
  ["null body", () => Promise.resolve(response(null))],
  ["missing policy", () => Promise.resolve(response({ policy: null }))],
  ["wrong rule shape", () => Promise.resolve(response({ policy: { ...policy, focus_rules: "robotics" } }))],
  ["missing rule list", () => Promise.resolve(response({ policy: { ...policy, ignore_rules: null } }))],
  ["wrong rule member", () => Promise.resolve(response({ policy: { ...policy, focus_rules: [123] } }))],
  ["missing numeric setting", () => Promise.resolve(response({ policy: { ...policy, per_run_max_new_videos: undefined } }))],
  ["unknown style", () => Promise.resolve(response({ policy: { ...policy, distillation_style: "UNKNOWN" } }))],
])("never calls failed %s policy Not set or saves inherited configuration", async (_name, failed) => {
  const fetcher = vi.fn(failed);
  vi.stubGlobal("fetch", fetcher);
  form();
  expect((await screen.findByRole("alert")).textContent).toContain("Global interests could not be loaded");
  expect(screen.queryByText(/Not set/)).toBeNull();
  expect(save().disabled).toBe(true);
  fireEvent.submit(save().closest("form")!);
  expect(fetcher.mock.calls).toHaveLength(1);
});
it("retries only the GET, tolerates another failure, and preserves all edited drafts", async () => {
  const fetcher = vi.fn().mockRejectedValueOnce(new TypeError("Failed to fetch")).mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValue(response({ policy }));
  vi.stubGlobal("fetch", fetcher);
  form();
  await screen.findByRole("alert");
  fireEvent.change(screen.getByLabelText("Focus preference"), { target: { value: "OVERRIDE" } });
  fireEvent.change(screen.getByLabelText("Focus"), { target: { value: "my draft" } });
  fireEvent.change(screen.getByLabelText("Initial history"), { target: { value: "3" } });
  fireEvent.change(screen.getByLabelText("Schedule time"), { target: { value: "12:34" } });
  fireEvent.click(screen.getByRole("button", { name: "Retry global interests" }));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  await screen.findByRole("alert");
  expect(save().disabled).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Retry global interests" }));
  await screen.findByText("Global ignore: sponsored");
  expect(save().disabled).toBe(false);
  expect((screen.getByLabelText("Focus") as HTMLInputElement).value).toBe("my draft");
  expect((screen.getByLabelText("Initial history") as HTMLSelectElement).value).toBe("3");
  expect((screen.getByLabelText("Schedule time") as HTMLInputElement).value).toBe("12:34");
  expect(fetcher.mock.calls.map(([path, init]) => [path, init.method ?? "GET"])) .toEqual(Array(3).fill(["/api/v1/settings/source-policy", "GET"]));
});
it("shows Not set only after a valid policy actually has no focus or ignore words", async () => {
  vi.stubGlobal("fetch", vi.fn(async () => response({ policy: { ...policy, focus_rules: [], ignore_rules: [] } })));
  form();
  await screen.findByText("Global focus: Not set");
  expect(screen.getByText("Global ignore: Not set")).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
  expect(save().disabled).toBe(false);
});
it("localizes the read explanation and retry action in Chinese", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  form();
  expect((await screen.findByRole("alert")).textContent).toContain("未能加载全局兴趣");
  expect(screen.getByRole("button", { name: "重试加载全局兴趣" })).toBeTruthy();
  expect(screen.queryByText(/尚未设置/)).toBeNull();
});
it("ignores a read settling after unmount and reads fresh policy on return", async () => {
  let resolve!: (value: ReturnType<typeof response>) => void;
  const fetcher = vi.fn().mockImplementationOnce(() => new Promise(r => { resolve = r; })).mockResolvedValue(response({ policy }));
  vi.stubGlobal("fetch", fetcher);
  const opened = form();
  opened.unmount();
  await act(async () => resolve(response({})));
  form();
  await screen.findByText("Global focus: robotics");
  expect(fetcher).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole("alert")).toBeNull();
});

it.each(["focus", "ignore", "style"] as const)("blocks a save when only %s still inherits unread policy", async key => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  form({ focus: "OVERRIDE", ignore: "OVERRIDE", style: "OVERRIDE", [key]: "INHERIT" });
  await screen.findByRole("alert");
  expect(save().disabled).toBe(true);
});
it("keeps fully explicit policy editing independent of an unavailable global read", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  form({ focus: "OVERRIDE", ignore: "OVERRIDE", style: "OVERRIDE" });
  await screen.findByRole("alert");
  expect(save().disabled).toBe(false);
  expect((screen.getByLabelText("Focus") as HTMLInputElement).value).toBe("robotics");
});
