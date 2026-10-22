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
afterEach(() => { vi.useRealTimers(); cleanup(); vi.unstubAllGlobals(); localStorage.clear(); location.hash = ""; });
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

// Fake-clock cases flush mutations with act, then use synchronous accessible
// queries; async findBy's polling timer must not be stranded on that clock.
function openConfirmationNow(view: ReturnType<typeof within>, language: string) {
  fireEvent.click(view.getByRole("button", { name: language === "en" ? "Restore this backup…" : "恢复此备份…" }));
  const dialog = within(view.getByRole("dialog"));
  fireEvent.change(dialog.getByLabelText(language === "en" ? "Type RESTORE to confirm" : "输入 RESTORE 以确认"), { target: { value: "RESTORE" } });
  return dialog;
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
  vi.useFakeTimers();
  readFails = true;
  await act(async () => finish(await response({})));
  expect(view.getByText("Reconnecting and validating the restored data…")).toBeTruthy();
  expect(view.queryByRole("alert")).toBeNull();
  expect(view.getByText("Restore is pending. Intelligence will restart and validate the restored data before processing resumes.")).toBeTruthy();
  await act(async () => vi.advanceTimersByTimeAsync(60_001));
  expect(view.getByText("Backup status is unavailable. Check the local connection and retry.")).toBeTruthy();
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  vi.useRealTimers();
  readFails = false;
  status = ready({ restore_id: "current-restore", state: "APPLIED", message: "new receipt", completed_at: "2026-10-14T12:00:00Z" });
  fireEvent.click(view.getByRole("button", { name: "Retry" }));
  await view.findByText(currentCopy("en"));
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect(fetch.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(2);
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});

it.each(["en", "zh-CN"])("reconnects by GET after the acknowledged restore without replaying confirmation in %s", async language => {
  vi.useFakeTimers();
  let status: object = ready();
  let disconnected = false;
  const fetch = open(language, () => disconnected ? Promise.reject(new Error("expected local restart")) : response({ status }), path => {
    if (path.endsWith("/stage")) return response(stage);
    if (path.endsWith("/confirm")) disconnected = true;
    return response({ restore: { restore_id: "current-restore", restart_required: true } });
  });
  await act(async () => {});
  const view = within(screen.getByRole("heading", { name: language === "en" ? "Backup and Restore" : "备份与恢复" }).closest("section")!);
  choose(view, language);
  await act(async () => {});
  const dialog = openConfirmationNow(view, language);
  fireEvent.click(dialog.getByRole("button", { name: language === "en" ? "Confirm Restore and restart" : "确认恢复并重启" }));
  await act(async () => {});
  expect(view.getByText(language === "en" ? "Reconnecting and validating the restored data…" : "正在重新连接并验证恢复的数据…")).toBeTruthy();
  expect(view.queryByRole("alert")).toBeNull();
  disconnected = false;
  status = ready({ restore_id: "current-restore", state: "APPLIED", completed_at: "2026-10-21T13:00:00Z" });
  await act(async () => vi.advanceTimersByTimeAsync(10_000));
  expect(view.getByText(currentCopy(language))).toBeTruthy();
  expect(view.queryByText(language === "en" ? "Reconnecting and validating the restored data…" : "正在重新连接并验证恢复的数据…")).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
  expect(fetch.mock.calls.filter(([, init]) => init?.method === "POST").map(([path]) => path)).toEqual([
    "/api/v1/backup-restore/restore/stage", "/api/v1/backup-restore/restore/confirm",
  ]);
});

it.each(["REJECTED", "ROLLED_BACK", "UNKNOWN_FUTURE"])("keeps a matching terminal restore failure explicit: %s", async state => {
  let status: object = ready();
  const fetch = open("en", () => response({ status }), path => {
    if (path.endsWith("/stage")) return response(stage);
    if (path.endsWith("/confirm")) status = { ...ready({ state, restore_id: "current-restore" }), ready: false };
    return response({ restore: { restore_id: "current-restore", restart_required: true } });
  });
  const view = within(await panel("en"));
  await act(async () => {});
  choose(view, "en");
  const dialog = await openConfirmation(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await view.findByText("Restore did not complete successfully. Read its status before trying again.");
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(view.getByRole("button", { name: "Retry" })).toBeTruthy();
  fireEvent.click(view.getByRole("button", { name: "Retry" }));
  await act(async () => {});
  expect(view.getByText("Restore did not complete successfully. Read its status before trying again.")).toBeTruthy();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});

it("labels source media length separately from processing duration", async () => {
  localStorage.setItem("yia.ui-language", "zh-CN");
  localStorage.setItem("intelligence.onboarding.completed.v1", "true");
  location.hash = "#Content/media-time";
  vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/videos/media-time")
    ? response({ video: { video_id: "media-time", provider: "LOCAL", title: "Local movie", media_kind: "VIDEO", format: ".mp4", duration_seconds: 22.565, processing_status: "COMPLETED" }, transcript: { status: "UNAVAILABLE" }, note: { v1: { status: "UNAVAILABLE" }, v2: { status: "UNAVAILABLE" } }, intelligence_result: { status: "NOT_PROCESSED" }, history: [] })
    : response({ evidence: [] })));
  render(<App />);
  await screen.findByText("时长: 23s");
  expect(screen.queryByText("耗时: 23s")).toBeNull();
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

it.each(["en", "zh-CN"])("distinguishes integrity and unknown blockers while preserving every unfinished reason in %s", async language => {
  const fetch = open(language, () => response({ status: { ready: false, reasons: ["DATABASE_UNAVAILABLE", "JOBS_ACTIVE", "TRACKED_CONTENT_RETRY_ACTIVE", "FUTURE_REASON"], message: "/private/raw/internal-error", restore_pending: false } }));
  const view = within(await panel(language));
  const copy = language === "en" ? ["Backup is unavailable for these reasons:", "Stored files or the database could not be verified. Check local storage and retry.", "a background job is still running", "a caption retry is still unfinished", "Backup safety has not been confirmed. Read its status again."] : ["以下原因导致暂时无法备份：", "无法验证已保存文件或数据库的完整性。请检查本地存储后重试。", "有一个后台任务仍在执行", "有一个字幕重试尚未结束", "尚未确认备份是否安全，请重新读取状态。"];
  await waitFor(() => copy.forEach(text => expect(view.getByRole("status").textContent).toContain(text)));
  expect(view.queryByText(/private\/raw/)).toBeNull();
  expect((view.getByRole("button", { name: language === "en" ? "Create Backup" : "创建备份" }) as HTMLButtonElement).disabled).toBe(true);
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});

it.each([{ reasons: [] }, { reasons: ["FUTURE_REASON"] }, { reasons: ["DATABASE_UNAVAILABLE"] }])("does not attribute closed readiness to running work without evidence: %j", async ({ reasons }) => {
  open("en", () => response({ status: { ready: false, reasons, restore_pending: false } }));
  const view = within(await panel("en"));
  await view.findByText(reasons.includes("DATABASE_UNAVAILABLE") ? /Stored files or the database could not be verified/ : /Backup safety has not been confirmed/);
  expect(view.getByRole("status").textContent).not.toMatch(/work.*(flight|unfinished)|job.*running/);
  expect((view.getByRole("button", { name: "Create Backup" }) as HTMLButtonElement).disabled).toBe(true);
});


it("preserves integrity and work blockers alongside a pending restore", async () => {
  open("en", () => response({ status: { ready: false, reasons: ["DATABASE_UNAVAILABLE", "JOBS_ACTIVE"], restore_pending: true } }));
  const view = within(await panel("en"));
  await waitFor(() => {
    const text = view.getByText(/Backup is unavailable for these reasons/).textContent;
    expect(text).toContain("a restore is pending");
    expect(text).toContain("Stored files or the database could not be verified");
    expect(text).toContain("a background job is still running");
  });
  expect((view.getByRole("button", { name: "Create Backup" }) as HTMLButtonElement).disabled).toBe(true);
});


it.each(["en", "zh-CN"])("identifies known local maintenance without alleging database corruption in %s", async language => {
  open(language, () => response({ status: { ...ready(), ready: false, reasons: ["MAINTENANCE_ACTIVE"] } }));
  const view = within(await panel(language));
  await view.findByText(language === "en" ? /another Backup, Restore or model configuration operation is in progress/ : /另一个备份、恢复或模型配置操作正在进行/);
  expect(view.queryByText(/Stored files or the database|无法验证已保存文件/)).toBeNull();
  expect((view.getByRole("button", { name: language === "en" ? "Create Backup" : "创建备份" }) as HTMLButtonElement).disabled).toBe(true);
});

it("keeps acknowledged reconnect bounded when no matching receipt arrives", async () => {
  vi.useFakeTimers();
  const fetch = open("en", () => response({ status: ready() }), path => path.endsWith("/stage") ? response(stage) : response({ restore: { restore_id: "current-restore" } }));
  await act(async () => {});
  const view = within(screen.getByRole("heading", { name: "Backup and Restore" }).closest("section")!);
  choose(view, "en");
  await act(async () => {});
  const dialog = openConfirmationNow(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await act(async () => {});
  expect(view.getByText("Reconnecting and validating the restored data…")).toBeTruthy();
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  await act(async () => vi.advanceTimersByTimeAsync(60_001));
  expect(view.getByText("Backup status is unavailable. Check the local connection and retry.")).toBeTruthy();
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});

it("does not let a pre-acknowledgement read overwrite the matching applied receipt", async () => {
  vi.useFakeTimers();
  let reads = 0;
  let finishOld!: (value: Awaited<ReturnType<typeof response>>) => void;
  let status: object = ready();
  open("en", () => ++reads === 2 ? new Promise(resolve => { finishOld = resolve; }) : response({ status }), path => {
    if (path.endsWith("/stage")) return response(stage);
    status = ready({ restore_id: "current-restore", state: "APPLIED", completed_at: "2026-10-22T12:00:00Z" });
    return response({ restore: { restore_id: "current-restore" } });
  });
  await act(async () => {});
  const view = within(screen.getByRole("heading", { name: "Backup and Restore" }).closest("section")!);
  choose(view, "en");
  await act(async () => {});
  const dialog = openConfirmationNow(view, "en");
  await act(async () => vi.advanceTimersByTimeAsync(10_000));
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await act(async () => {});
  expect(view.getByText(currentCopy("en"))).toBeTruthy();
  await act(async () => finishOld(await response({ status: { ...ready(), restore_pending: true } })));
  expect(view.getByText(currentCopy("en"))).toBeTruthy();
  expect(view.queryByText("Restore is pending. Intelligence will restart and validate the restored data before processing resumes.")).toBeNull();
});


it("rejects an acknowledgement for another restore without entering the neutral reconnect window", async () => {
  const fetch = open("en", () => response({ status: ready() }), path => path.endsWith("/stage") ? response(stage) : response({ restore: { restore_id: "different-restore" } }));
  const view = within(await panel("en"));
  await act(async () => {});
  choose(view, "en");
  const dialog = await openConfirmation(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await view.findByText("Restore confirmation failed. Check restore status before trying again.");
  expect(view.queryByText("Reconnecting and validating the restored data…")).toBeNull();
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});


it.each(["REJECTED", "ROLLED_BACK", "UNKNOWN_FUTURE"].flatMap(state =>
  ["disconnect", "unrelated receipt"].map(next => ({ state, next }))))("retains known terminal failure after $state then $next", async ({ state, next }) => {
  vi.useFakeTimers();
  let status: object = ready();
  let disconnected = false;
  const fetch = open("en", () => disconnected ? Promise.reject(new Error("later connection lost")) : response({ status }), path => {
    if (path.endsWith("/stage")) return response(stage);
    status = { ...ready({ restore_id: "current-restore", state }), ready: false };
    return response({ restore: { restore_id: "current-restore" } });
  });
  await act(async () => {});
  const view = within(screen.getByRole("heading", { name: "Backup and Restore" }).closest("section")!);
  choose(view, "en");
  await act(async () => {});
  const dialog = openConfirmationNow(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await act(async () => {});
  expect(view.getByText("Restore did not complete successfully. Read its status before trying again.")).toBeTruthy();
  disconnected = next === "disconnect";
  status = ready();
  await act(async () => vi.advanceTimersByTimeAsync(10_000));
  expect(view.getByText("Restore did not complete successfully. Read its status before trying again.")).toBeTruthy();
  expect(view.getByRole("button", { name: "Retry" })).toBeTruthy();
  expect(view.queryByText("Reconnecting and validating the restored data…")).toBeNull();
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});

it("retains the confirmed binding through an unrelated historical receipt until the matching APPLIED receipt", async () => {
  vi.useFakeTimers();
  let status: object = ready();
  const fetch = open("en", () => response({ status }), path => path.endsWith("/stage") ? response(stage) : response({ restore: { restore_id: "current-restore" } }));
  await act(async () => {});
  const view = within(screen.getByRole("heading", { name: "Backup and Restore" }).closest("section")!);
  choose(view, "en");
  await act(async () => {});
  const dialog = openConfirmationNow(view, "en");
  fireEvent.click(dialog.getByRole("button", { name: "Confirm Restore and restart" }));
  await act(async () => {});
  expect(view.getByText("Reconnecting and validating the restored data…")).toBeTruthy();
  expect(view.queryByText(currentCopy("en"))).toBeNull();
  status = ready({ restore_id: "current-restore", state: "APPLIED", completed_at: "2026-10-23T02:00:00Z" });
  await act(async () => vi.advanceTimersByTimeAsync(10_000));
  expect(view.getByText(currentCopy("en"))).toBeTruthy();
  expect(view.queryByText(previousCopy("en"))).toBeNull();
  expect(fetch.mock.calls.filter(([path]) => path.endsWith("/confirm"))).toHaveLength(1);
});
