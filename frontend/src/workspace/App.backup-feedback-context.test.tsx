import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

const response = (body: object) => Promise.resolve({ ok: true, json: async () => body });
const oldReceipt = { restore_id: "previous-restore", state: "APPLIED", message: "opaque service prose", completed_at: "2026-10-10T12:00:00Z" };
const ready = (receipt: object | null = oldReceipt) => ({ ready: true, reasons: [], restore_pending: false, last_restore: receipt });
const preview = { backup_date: "2026-10-10T12:00:00Z", application_version: "test", schema_version: 38, following_count: 1, content_count: 2, summary_count: 1, evidence_count: 2, intelligence_count: 0, topic_count: 0, settings_included: true, data_artifact_count: 3, data_size_bytes: 100, vault_excluded: true };
const currentCopy = (language: string) => language === "en" ? "Restore completed successfully." : "备份已恢复，重启后的数据检查已通过。";
const previousCopy = (language: string) => language === "en" ? "Previous restore completed successfully." : "上一次恢复已完成，重启后的数据检查已通过。";
const stage = { restore: { restore_id: "current-restore", preview } };
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });
function open(language: string, read: () => ReturnType<typeof response>, mutation: (path: string) => ReturnType<typeof response> = () => response({})) {
  localStorage.setItem("yia.ui-language", language);
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Settings";
  const fetch = vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/backup-restore/status")) return read();
    if (init?.method === "POST") return mutation(path);
    if (path.endsWith("/settings")) return response({ general: { timezone: "Asia/Shanghai", output_language: "zh-CN", output_language_source: "BOOTSTRAP_DEFAULT", output_language_updated_at: null }, providers: [] });
    if (path.endsWith("/settings/preferences")) return response({ active: [], history: [] });
    if (path.endsWith("/settings/source-policy")) return response({ policy: { initial_history_count: 5, per_run_max_new_videos: 5, focus_rules: [], ignore_rules: [], distillation_style: "BALANCED" } });
    if (path.endsWith("/settings/resource-usage")) return response({ usage: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetch);
  render(<App />);
  return fetch;
}
async function panel(language: string) {
  return (await screen.findByRole("heading", { name: language === "en" ? "Backup and Restore" : "备份与恢复" })).closest("section")!;
}
function choose(view: ReturnType<typeof within>, language: string) {
  fireEvent.change(view.getByLabelText(language === "en" ? "Choose backup file" : "选择备份文件"), { target: { files: [new File(["PK"], "next.zip", { type: "application/zip" })] } });
}
async function openConfirmation(view: ReturnType<typeof within>, language: string) {
  fireEvent.click(await view.findByRole("button", { name: language === "en" ? "Restore this backup…" : "恢复此备份…" }));
  const dialog = await view.findByRole("dialog");
  fireEvent.change(within(dialog).getByLabelText(language === "en" ? "Type RESTORE to confirm" : "输入 RESTORE 以确认"), { target: { value: "RESTORE" } });
  return within(dialog);
}

it.each(["en", "zh-CN"])("labels an applied receipt as previous on initial reading in %s", async language => {
  const fetch = open(language, () => response({ status: ready() }));
  const view = within(await panel(language));
  await view.findByText(previousCopy(language));
  expect(view.getByText(/2026/)).toBeTruthy();
  expect(view.queryByText(currentCopy(language))).toBeNull();
  expect(view.queryByText("opaque service prose")).toBeNull();
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each(["en", "zh-CN"])("hides previous success during inspection and confirmation and restores history after cancel in %s", async language => {
  let finish!: (value: Awaited<ReturnType<typeof response>>) => void;
  const fetch = open(language, () => response({ status: ready() }), path => path.endsWith("/stage") ? new Promise(resolve => { finish = resolve; }) : response({}));
  const view = within(await panel(language));
  await waitFor(() => expect(fetch.mock.calls.some(([path]) => path.endsWith("/backup-restore/status"))).toBe(true));
  await act(async () => {});
  choose(view, language);
  expect(view.queryByText(currentCopy(language))).toBeNull();
  expect(view.queryByText(previousCopy(language))).toBeNull();
  await act(async () => finish(await response(stage)));
  const dialog = await openConfirmation(view, language);
  expect(view.queryByText(currentCopy(language))).toBeNull();
  expect(view.queryByText(previousCopy(language))).toBeNull();
  fireEvent.click(dialog.getByRole("button", { name: language === "en" ? "Go back" : "返回" }));
  fireEvent.click(view.getByRole("button", { name: language === "en" ? "Cancel" : "取消" }));
  await view.findByText(previousCopy(language));
  expect(view.queryByText(currentCopy(language))).toBeNull();
  const writes = fetch.mock.calls.filter(([, init]) => init?.method === "POST");
  expect(writes.map(([path]) => path)).toEqual(["/api/v1/backup-restore/restore/stage", "/api/v1/backup-restore/restore/cancel"]);
  expect(JSON.parse(String(writes[1][1]?.body))).toEqual({ restore_id: "current-restore" });
});

it.each(["en", "zh-CN"])("never reports an old applied receipt as success while restore is pending in %s", async language => {
  const fetch = open(language, () => response({ status: { ...ready(), ready: false, restore_pending: true, reasons: ["RESTORE_PENDING"] } }));
  const view = within(await panel(language));
  await view.findByText(language === "en" ? "Restore is pending. Intelligence will restart and validate the restored data before processing resumes." : "恢复待完成；应用将重启并验证恢复的数据，然后继续处理。" );
  expect(view.queryByText(currentCopy(language))).toBeNull();
  expect(view.queryByText(previousCopy(language))).toBeNull();
  expect((view.getByRole("button", { name: language === "en" ? "Create Backup" : "创建备份" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each(["current-restore", "different-restore", null])("only reports this operation complete for its actual matching applied receipt: %s", async receiptId => {
  let status: object = ready();
  const fetch = open("en", () => response({ status }), path => {
    if (path.endsWith("/stage")) return response(stage);
    if (path.endsWith("/confirm")) status = ready({ state: "APPLIED", ...(receiptId ? { restore_id: receiptId } : {}), completed_at: "2026-10-14T12:00:00Z", message: "new receipt" });
    return response({});
  });
  const view = within(await panel("en"));
  await act(async () => {});
  choose(view, "en");
  const dialog = await openConfirmation(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await waitFor(() => expect(fetch.mock.calls.some(([path]) => path.endsWith("/confirm"))).toBe(true));
  await view.findByText(receiptId === "current-restore" ? currentCopy("en") : previousCopy("en"));
  expect(view.queryByText(receiptId === "current-restore" ? previousCopy("en") : currentCopy("en"))).toBeNull();
  const confirms = fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"));
  expect(confirms).toHaveLength(1);
  expect(JSON.parse(String(confirms[0][1]?.body))).toEqual({ restore_id: "current-restore" });
});

it("preserves confirmation failure and does not replay it or label old receipt as current success", async () => {
  const fetch = open("en", () => response({ status: ready() }), path => path.endsWith("/stage") ? response(stage) : Promise.reject(new Error("unknown confirmation outcome")));
  const view = within(await panel("en"));
  await act(async () => {});
  choose(view, "en");
  const dialog = await openConfirmation(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await view.findByText("Restore confirmation failed. Check restore status before trying again.");
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});

it.each(["FAILED", "UNKNOWN_FUTURE"])("keeps a non-applied receipt %s from implying completion", async state => {
  const fetch = open("en", () => response({ status: { ...ready({ state, message: "unknown receipt" }), ready: false, reasons: ["JOBS_ACTIVE"] } }));
  const view = within(await panel("en"));
  await view.findByText(/a background job is still running/);
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect((view.getByRole("button", { name: "Create Backup" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it("keeps a failed status read explicit and does not imply ready or restore completion", async () => {
  const fetch = open("en", () => Promise.reject(new Error("read unavailable")));
  const view = within(await panel("en"));
  await view.findByText("Backup status is unavailable. Check the local connection and retry.");
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect(view.queryByText("Core data is quiescent and ready for backup.")).toBeNull();
  expect((view.getByRole("button", { name: "Create Backup" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});


it("does not claim readiness or stale restore success after a later status read fails", async () => {
  let reads = 0;
  const fetch = open("en", () => ++reads === 1 ? response({ status: ready() }) : Promise.reject(new Error("later read failure")), () => response({ backup: { backup_id: "new-backup", file_name: "new.zip", size_bytes: 100, created_at: "2026-10-14T12:00:00Z", preview } }));
  const view = within(await panel("en"));
  await act(async () => {});
  fireEvent.click(view.getByRole("button", { name: "Create Backup" }));
  await view.findByText("Backup status is unavailable. Check the local connection and retry.");
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect(view.queryByText("Core data is quiescent and ready for backup.")).toBeNull();
  expect(fetch.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
});

it.each(["en", "zh-CN"])("gives neutral source/processing guidance for a final invalid subtitle response in %s", async language => {
  localStorage.setItem("yia.ui-language", language);
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/rejected";
  const fetch = vi.fn((path: string, _init?: RequestInit) => {
    if (path.endsWith("/videos/rejected")) return response({ video: { video_id: "rejected", provider: "YOUTUBE", title: "Rejected captions", source_id: "one-video-source", processing_status: "FAILED", retry_allowed: true, processing_job: { status: "FAILED_FINAL", stage: "TRANSCRIPT", error_code: "INVALID_RESPONSE" } }, transcript: { status: "UNAVAILABLE" }, note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] });
    if (path.endsWith("/evidence")) return response({ evidence: [] });
    if (path.endsWith("/videos")) return response({ videos: [] });
    return response({});
  });
  vi.stubGlobal("fetch", fetch); render(<App />);
  await screen.findByText(language === "en" ? "Processing needs attention. Check the source and processing history before retrying; retry may still fail." : "处理需要关注。请先核对来源和处理记录，再决定是否重试；重试仍可能失败。");
  expect(screen.queryByText(language === "en" ? "Processing needs attention. Retry this Content when the connection is available." : "处理需要关注。网络恢复后，可重试此内容。")).toBeNull();
  expect(screen.queryByText(/4096|4,096|1024|1,024/)).toBeNull();
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each([
  { state: "APPLIED", message: "historical record without identity" },
  { state: "UNKNOWN_FUTURE", restore_id: "previous-restore", message: "unknown prior receipt" },
])("does not infer this restore completed from an unknown receipt baseline: %j", async previous => {
  let status: object = ready(previous);
  open("en", () => response({ status }), path => {
    if (path.endsWith("/stage")) return response(stage);
    if (path.endsWith("/confirm")) status = ready({ state: "APPLIED", restore_id: "current-restore", completed_at: "2026-10-14T12:00:00Z", message: "new receipt" });
    return response({});
  });
  const view = within(await panel("en"));
  await act(async () => {});
  choose(view, "en");
  const dialog = await openConfirmation(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await view.findByText(previousCopy("en"));
  expect(view.queryByText(currentCopy("en"))).toBeNull();
});

it("does not treat a reused already-applied preview identity as new completion", async () => {
  open("en", () => response({ status: ready() }), path => path.endsWith("/stage") ? response({ restore: { restore_id: oldReceipt.restore_id, preview } }) : response({}));
  const view = within(await panel("en"));
  await act(async () => {});
  choose(view, "en");
  const dialog = await openConfirmation(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await view.findByText(previousCopy("en"));
  expect(view.queryByText(currentCopy("en"))).toBeNull();
});

it("retains pending/error feedback while confirming and acknowledges the matching applied receipt only after successful GET", async () => {
  let finish!: (value: Awaited<ReturnType<typeof response>>) => void;
  let status: object = ready();
  let readFails = false;
  const fetch = open("en", () => readFails ? Promise.reject(new Error("restart status unavailable")) : response({ status }), path => path.endsWith("/stage") ? response(stage) : new Promise(resolve => { finish = resolve; }));
  const view = within(await panel("en"));
  await act(async () => {});
  choose(view, "en");
  const dialog = await openConfirmation(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  readFails = true;
  await act(async () => finish(await response({})));
  await view.findByText("Backup status is unavailable. Check the local connection and retry.");
  await view.findByText("Restore is pending. Intelligence will restart and validate the restored data before processing resumes.");
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  readFails = false;
  status = ready({ restore_id: "current-restore", state: "APPLIED", message: "new receipt", completed_at: "2026-10-14T12:00:00Z" });
  fireEvent.click(view.getByRole("button", { name: "Retry" }));
  await view.findByText(currentCopy("en"));
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect(fetch.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(2);
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});

it.each(["en", "zh-CN"])("does not reuse a completed operation's success after a later ZIP inspection fails in %s", async language => {
  let status: object = ready();
  let stages = 0;
  const fetch = open(language, () => response({ status }), path => {
    if (path.endsWith("/stage")) return ++stages === 1 ? response(stage) : Promise.reject(new Error("second archive inspection failed"));
    if (path.endsWith("/confirm")) status = ready({ restore_id: "current-restore", state: "APPLIED", message: "completed first operation", completed_at: "2026-10-14T12:00:00Z" });
    return response({ backup: { backup_id: "next-backup", file_name: "next.zip", size_bytes: 100, created_at: "2026-10-14T12:05:00Z", preview } });
  });
  const view = within(await panel(language));
  await act(async () => {});
  choose(view, language);
  const dialog = await openConfirmation(view, language);
  fireEvent.click(dialog.getByRole("button", { name: language === "en" ? "Confirm Restore and restart" : "确认恢复并重启" }));
  await view.findByText(currentCopy(language));
  choose(view, language);
  await view.findByText(language === "en" ? "Backup inspection failed. Choose an intact Intelligence ZIP backup; current data has not changed." : "备份检查未通过，请选择完整的 Intelligence ZIP 备份；当前数据未改变。");
  expect(view.queryByText(currentCopy(language))).toBeNull();
  expect(view.queryByText(previousCopy(language))).toBeNull();
  expect(view.getByRole("alert")).toBeTruthy();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
  // A later explicit action clears the inspection error, but must not revive
  // the obsolete "this operation completed" context for the prior receipt.
  fireEvent.click(view.getByRole("button", { name: language === "en" ? "Create Backup" : "创建备份" }));
  await view.findByText(previousCopy(language));
  expect(view.queryByText(currentCopy(language))).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
  expect(fetch.mock.calls.filter(([, init]) => init?.method === "POST").map(([path]) => path)).toEqual([
    "/api/v1/backup-restore/restore/stage", "/api/v1/backup-restore/restore/confirm", "/api/v1/backup-restore/restore/stage", "/api/v1/backup-restore/backups",
  ]);
});
