import { MutableRefObject, useState } from "react";
import { ApiRequestError, post } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

type RetryReceipt = {
  request_id: string; video_id: string; source_id: string; expected_job_id: string;
  target_job_id: string; state: string; revision: number; error_code: string | null;
  can_resume_local: boolean; can_close_local: boolean; can_cancel: boolean;
};
type RetryStatus = { request: RetryReceipt | null; retry_allowed: boolean; expected_job_id: string | null; error_code?: string };
const states = ["QUEUED", "ACQUIRING", "FINALIZING", "ATTENTION", "SUCCEEDED", "FAILED", "CANCELLED", "AMBIGUOUS"];
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
function receipt(value: unknown, id: string): value is RetryReceipt {
  if (!object(value) || value.video_id !== id || typeof value.state !== "string" || !states.includes(value.state)
    || !["request_id", "source_id", "expected_job_id", "target_job_id"].every(key => typeof value[key] === "string" && value[key])
    || !Number.isSafeInteger(value.revision) || (value.revision as number) < 0
    || !(value.error_code === null || typeof value.error_code === "string")
    || !["can_resume_local", "can_close_local", "can_cancel"].every(key => typeof value[key] === "boolean")) return false;
  return (!value.can_resume_local || value.state === "ATTENTION") && (!value.can_close_local || value.state === "ATTENTION") && (!value.can_cancel || value.state === "QUEUED");
}
export function readTrackedRetry(value: unknown, id: string): RetryStatus | null {
  if (!object(value) || typeof value.retry_allowed !== "boolean" || !(value.expected_job_id === null || typeof value.expected_job_id === "string")
    || !(value.request === null || receipt(value.request, id)) || (value.error_code !== undefined && value.error_code !== "RETRY_INTEGRITY_INVALID")
    || (value.retry_allowed && !value.expected_job_id)) return null;
  return value as RetryStatus;
}
export function trackedRetryActive(value: unknown, id: string) {
  const state = readTrackedRetry(value, id)?.request?.state;
  return !!state && ["QUEUED", "ACQUIRING", "FINALIZING"].includes(state);
}
const copy: Record<string, string> = {
  QUEUED: "Caption retry is queued. You can cancel before reading begins.",
  ACQUIRING: "Reading this Content's native captions…",
  FINALIZING: "Captions are saved. Preparing source references and Summary locally…",
  ATTENTION: "Captions are saved, but local organization needs attention. Retry local organization or finish this attempt and keep the captured text.",
  SUCCEEDED: "Captions, source references and Summary are ready.",
  FAILED: "This caption retry ended without completing Content organization. Captured text and processing history are preserved.",
  CANCELLED: "Caption retry was cancelled before reading began.",
  AMBIGUOUS: "The previous caption request's result is unknown. It will not be sent again automatically. Captured text and history are preserved.",
};
const errorCopy: Record<string, string> = {
  SOURCE_PAUSED: "This Following is paused. Resume it before requesting a new caption retry.",
  SOURCE_CONTEXT_CHANGED: "The followed source changed. Check its settings and refresh this Content.",
  RETRY_CONTRACT_UNAVAILABLE: "This caption retry needs a compatible local service. Restart the application, then read its status again.",
  NATIVE_TIMING_UNAVAILABLE: "Native timed captions were unavailable. Captured text is kept; no speech or cloud service was started.",
  LOCAL_FINALIZATION_LIMIT: "Local organization reached its retry limit. You can finish this attempt and keep the captured text.",
  LOCAL_FINALIZATION_CLOSED: "Local organization was ended. Captured text and processing history are preserved.",
};
export function TrackedContentRetry({ id, value, onRefresh, commands }: {
  id: string; value: unknown; onRefresh: () => void; commands: MutableRefObject<Map<string, string>>;
}) {
  const { t } = useUiLanguage();
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  if (value === undefined) return null;
  const status = readTrackedRetry(value, id);
  const invalid = !status || status.error_code === "RETRY_INTEGRITY_INVALID";
  if (!invalid && !status.request && !status.retry_allowed) return null;
  const current = status?.request;
  async function submit(operation?: string) {
    if (busy || invalid || !status) return;
    const input = operation && current
      ? { request_id: current.request_id, operation, expected_revision: current.revision }
      : { expected_job_id: status.expected_job_id };
    const key = `${id}:${JSON.stringify(input)}`;
    let command = commands.current.get(key);
    if (!command) { command = `ui:${Date.now()}:${Math.random().toString(36).slice(2)}`; commands.current.set(key, command); }
    setBusy(true); setFeedback(null);
    try {
      const response = await post<{ tracked_content_retry: unknown }>(`/content/${encodeURIComponent(id)}/retry${operation ? "/actions" : ""}`, { ...input, command_id: command });
      if (!receipt(response.tracked_content_retry, id)) throw new Error("Unverified receipt");
      setFeedback("Caption retry action accepted. Reading its current status…");
      onRefresh();
    } catch (error) {
      setFeedback(error instanceof ApiRequestError && error.code === "RETRY_CONFLICT"
        ? "Caption retry state changed or is busy. Read its current status before trying again."
        : "The caption retry result could not be confirmed. Read its current status; retrying this action keeps the same command.");
    } finally { setBusy(false); }
  }
  return <section className="panel" aria-label={t("Caption retry")}>
    <div className="panel-heading"><h2>{t("Caption retry")}</h2></div>
    <p role="status">{t(invalid ? "Caption retry evidence could not be verified. Read its status again; no new request will be sent." : current ? copy[current.state] : "Retry native captions for this followed Content. This reads only this video and prepares source references and an extractive Summary.")}</p>
    {!invalid && current?.error_code && errorCopy[current.error_code] && <p>{t(errorCopy[current.error_code])}</p>}
    <div className="button-row">
      {!invalid && status.retry_allowed && <button className="button button-secondary" disabled={busy} onClick={() => submit()}>{t("Retry captions")}</button>}
      {!invalid && current?.can_cancel && <button className="button button-secondary" disabled={busy} onClick={() => submit("CANCEL_BEFORE_DISPATCH")}>{t("Cancel caption retry")}</button>}
      {!invalid && current?.can_resume_local && <button className="button button-secondary" disabled={busy} onClick={() => submit("RESUME_LOCAL")}>{t("Retry local organization")}</button>}
      {!invalid && current?.can_close_local && <button className="button button-secondary" disabled={busy} onClick={() => submit("CLOSE_LOCAL")}>{t("Finish and keep captured text")}</button>}
      <button className="button button-ghost" disabled={busy} onClick={onRefresh}>{t("Read caption retry status")}</button>
    </div>
    {feedback && <p role="status">{t(feedback)}</p>}
  </section>;
}
