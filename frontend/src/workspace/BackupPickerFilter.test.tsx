import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { App } from "./App";

const hint = "Choose an Intelligence .zip backup. Invalid files are rejected; you can choose another file.";
const hintZh = "请选择 Intelligence 生成的 .zip 备份。无效文件会被拒绝，可重新选择。";
const preview = { backup_date: "2026-10-16T00:00:00Z", application_version: "test", schema_version: 39,
  following_count: 1, content_count: 1, summary_count: 1, evidence_count: 1, intelligence_count: 0,
  topic_count: 0, settings_included: true, data_artifact_count: 2, data_size_bytes: 100,
  data_file_count: 1, data_file_size_bytes: 100, vault_excluded: true };
const response = (body: object) => ({ ok: true, json: async () => body });

afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });

async function open(language: string, rejectArchive = false) {
  localStorage.setItem("yia.ui-language", language);
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Settings";
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith("/backup-restore/status")) return response({ status: { ready: true, reasons: [], restore_pending: false } });
    if (path.endsWith("/restore/stage")) return rejectArchive
      ? { ok: false, json: async () => ({ error: { message: "Archive rejected: invalid manifest or unsafe paths" } }) }
      : response({ restore: { restore_id: "inspection", preview } });
    if (path.endsWith("/restore/cancel")) return response({});
    if (init?.method === "POST") throw new Error(`Unexpected mutation ${path}`);
    if (path.endsWith("/settings")) return response({ general: { timezone: "Asia/Shanghai", output_language: "en" }, providers: [] });
    if (path.endsWith("/settings/preferences")) return response({ active: [], history: [] });
    if (path.endsWith("/settings/source-policy")) return response({ policy: { focus_rules: [], ignore_rules: [], distillation_style: "BALANCED", initial_history_count: 3, per_run_max_new_videos: 5 } });
    if (path.endsWith("/settings/resource-usage")) return response({ usage: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetcher);
  render(<App />);
  const view = within((await screen.findByRole("heading", { name: language === "en" ? "Backup and Restore" : "备份与恢复" })).closest("section")!);
  const input = view.getByLabelText(language === "en" ? "Choose backup file" : "选择备份文件") as HTMLInputElement;
  await waitFor(() => expect(fetcher.mock.calls.some(([path]) => path.endsWith("/backup-restore/status"))).toBe(true));
  return { view, input, fetcher, writes: () => fetcher.mock.calls.filter(([, init]) => init?.method === "POST") };
}

it.each(["en", "zh-CN"])("leaves native file filtering open and describes the ZIP requirement in %s", async language => {
  const { view, input, writes } = await open(language);
  expect(input.hasAttribute("accept")).toBe(false);
  expect(input.type).toBe("file");
  const description = view.getByText(language === "en" ? hint : hintZh);
  expect(input.getAttribute("aria-describedby")).toBe(description.id);
  expect(writes()).toHaveLength(0);
});

it.each(["en", "zh-CN"])("cancels without uploading and rejects misleading non-ZIP names before stage in %s", async language => {
  const { view, input, writes } = await open(language);
  fireEvent.change(input, { target: { files: [] } });
  expect(view.queryByRole("alert")).toBeNull();
  for (const name of ["backup.txt", "backup.zip.exe", "<script>alert(1)</script>.html"]) {
    fireEvent.change(input, { target: { files: [new File(["PK"], name, { type: "application/zip" })] } });
    await view.findByText(language === "en" ? "Choose an Intelligence ZIP backup." : "请选择 Intelligence 生成的 ZIP 备份文件。");
  }
  expect(writes()).toHaveLength(0);
  expect(view.queryByRole("dialog")).toBeNull();
});

it.each(["en", "zh-CN"])("keeps backend rejection explicit for untrusted ZIP bytes and permits a deliberate reselection in %s", async language => {
  const { view, input, writes } = await open(language, true);
  const file = new File(["not a zip; unsafe manifest"], "untrusted.zip", { type: "text/plain" });
  for (let count = 1; count <= 2; count++) {
    fireEvent.change(input, { target: { files: [file] } });
    await view.findByText(language === "en" ? "Backup inspection failed. Choose an intact Intelligence ZIP backup; current data has not changed." : "备份检查未通过，请选择完整的 Intelligence ZIP 备份；当前数据未改变。");
    expect(writes()).toHaveLength(count);
    expect(writes()[count - 1][1]?.body).toBe(file);
    expect(writes()[count - 1][1]?.headers).toMatchObject({ "Content-Type": "application/zip", "X-YIA-Request": "local-ui" });
    expect(input.value).toBe("");
    expect(view.queryByRole("button", { name: language === "en" ? "Restore this backup…" : "恢复此备份…" })).toBeNull();
  }
  expect(writes().every(([path]) => path.endsWith("/restore/stage"))).toBe(true);
});

it.each(["en", "zh-CN"])("stages ZIP without trusting MIME, preserves explicit confirmation and can reselect after cancellation in %s", async language => {
  const { view, input, writes } = await open(language);
  const file = new File(["fixture archive bytes"], "backup.ZIP");
  for (let count = 1; count <= 2; count++) {
    fireEvent.change(input, { target: { files: [file] } });
    const restore = await view.findByRole("button", { name: language === "en" ? "Restore this backup…" : "恢复此备份…" });
    expect(writes().filter(([path]) => path.endsWith("/restore/stage"))).toHaveLength(count);
    expect(writes().find(([path]) => path.endsWith("/restore/stage"))?.[1]?.body).toBe(file);
    expect(view.queryByRole("dialog")).toBeNull();
    fireEvent.click(restore);
    const dialog = within(await view.findByRole("dialog"));
    expect((dialog.getByRole("button", { name: language === "en" ? "Confirm Restore and restart" : "确认恢复并重启" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(dialog.getByRole("button", { name: language === "en" ? "Go back" : "返回" }));
    fireEvent.click(view.getByRole("button", { name: language === "en" ? "Cancel" : "取消" }));
    await waitFor(() => expect(view.queryByRole("button", { name: language === "en" ? "Restore this backup…" : "恢复此备份…" })).toBeNull());
  }
  expect(writes().map(([path]) => path)).toEqual(["/api/v1/backup-restore/restore/stage", "/api/v1/backup-restore/restore/cancel", "/api/v1/backup-restore/restore/stage", "/api/v1/backup-restore/restore/cancel"]);
});
