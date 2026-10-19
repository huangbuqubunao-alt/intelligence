import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { TrackedContentRetry, readTrackedRetry, trackedRetryActive } from "./TrackedContentRetry";
import { UiLanguageProvider } from "./uiLanguage";
const id = "trackedvideo1";
const receipt = (state = "QUEUED") => ({ request_id: "tracked-content-retry:v1:request", video_id: id, source_id: "source", expected_job_id: "old-job", target_job_id: "tracked-content-retry-job:v1:target", state, revision: 2, error_code: state === "ATTENTION" ? "LOCAL_FINALIZATION_FAILED" : state === "AMBIGUOUS" ? "DISPATCH_OUTCOME_UNKNOWN" : null, can_resume_local: state === "ATTENTION", can_close_local: state === "ATTENTION", can_cancel: state === "QUEUED" });
const status = (state: string) => ({ request: receipt(state), retry_allowed: false, expected_job_id: null });
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });
function open(value: unknown, language = "en") {
  localStorage.setItem("yia.ui-language", language);
  const refresh = vi.fn();
  const commands = { current: new Map<string, string>() };
  const view = render(<UiLanguageProvider><TrackedContentRetry id={id} value={value} commands={commands} onRefresh={refresh} /></UiLanguageProvider>);
  return { refresh, commands, ...view };
}
it.each(["en", "zh-CN"])("keeps one command after an uncertain response in %s", async language => {
  const calls: object[] = [];
  vi.stubGlobal("fetch", vi.fn(async (path, init) => { calls.push({ path, body: JSON.parse(init.body) }); throw new TypeError("connection lost"); }));
  const { commands } = open({ request: null, retry_allowed: true, expected_job_id: "old-job" }, language);
  const button = await screen.findByRole("button", { name: language === "en" ? "Retry captions" : "重试字幕" });
  fireEvent.click(button);
  await screen.findByText(language === "en" ? "The caption retry result could not be confirmed. Read its current status; retrying this action keeps the same command." : "未能确认字幕重试操作的结果。请重新读取状态；再次执行此操作会沿用同一请求。");
  fireEvent.click(button);
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls[0]).toEqual(calls[1]);
  expect(calls[0]).toEqual({ path: `/api/v1/content/${id}/retry`, body: { expected_job_id: "old-job", command_id: [...commands.current.values()][0] } });
});
it.each(["QUEUED", "ACQUIRING", "FINALIZING", "ATTENTION", "SUCCEEDED", "FAILED", "CANCELLED", "AMBIGUOUS"])("shows truthful %s without implicit requests", state => {
  const fetch = vi.fn(); vi.stubGlobal("fetch", fetch); open(status(state));
  expect(screen.getByRole("region", { name: "Caption retry" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Read caption retry status" })).toBeTruthy();
  expect(!!screen.queryByRole("button", { name: "Cancel caption retry" })).toBe(state === "QUEUED");
  expect(!!screen.queryByRole("button", { name: "Retry local organization" })).toBe(state === "ATTENTION");
  expect(fetch).not.toHaveBeenCalled();
  expect(trackedRetryActive(status(state), id)).toBe(["QUEUED", "ACQUIRING", "FINALIZING"].includes(state));
});
it.each(["RESUME_LOCAL", "CLOSE_LOCAL", "CANCEL_BEFORE_DISPATCH"])("submits only requested action %s", async operation => {
  const current = receipt(operation === "CANCEL_BEFORE_DISPATCH" ? "QUEUED" : "ATTENTION");
  const fetch = vi.fn(async (..._args: [string, RequestInit]) => ({ ok: true, json: async () => ({ tracked_content_retry: current }) }));
  vi.stubGlobal("fetch", fetch); const { refresh } = open({ request: current, retry_allowed: false, expected_job_id: null });
  fireEvent.click(screen.getByRole("button", { name: operation === "RESUME_LOCAL" ? "Retry local organization" : operation === "CLOSE_LOCAL" ? "Finish and keep captured text" : "Cancel caption retry" }));
  await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
  expect(fetch.mock.calls[0][0]).toBe(`/api/v1/content/${id}/retry/actions`);
  expect(JSON.parse(fetch.mock.calls[0][1].body as string)).toEqual({ operation, request_id: current.request_id, expected_revision: current.revision, command_id: expect.any(String) });
});
it.each([null, { request: null, retry_allowed: "yes", expected_job_id: "old" }, status("FUTURE"), { ...status("SUCCEEDED"), request: { ...receipt("SUCCEEDED"), can_resume_local: true } }, { ...status("ATTENTION"), request: { ...receipt("ATTENTION"), revision: false } }])("closes malformed status %j", value => {
  expect(readTrackedRetry(value, id)).toBeNull(); open(value);
  expect(screen.getAllByRole("button")).toHaveLength(1);
  expect(screen.getByText("Caption retry evidence could not be verified. Read its status again; no new request will be sent.")).toBeTruthy();
});
it("keeps close available at the local retry limit", () => {
  open({ ...status("ATTENTION"), request: { ...receipt("ATTENTION"), can_resume_local: false } });
  expect(screen.queryByRole("button", { name: "Retry local organization" })).toBeNull();
  expect(screen.getByRole("button", { name: "Finish and keep captured text" })).toBeTruthy();
});
