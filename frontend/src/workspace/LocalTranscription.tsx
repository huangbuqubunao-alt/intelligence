import { useEffect, useRef, useState } from "react";
import { api, ApiRequestError, post, put } from "../api/client";
import { useUiLanguage } from "./uiLanguage";
import { transcriptionGuidance } from "./TranscriptionSetup";

export type TranscriptionCapability = {
  state: string; runtime_detected: boolean; runtime_available: boolean;
  model_present: boolean; executor_compatible: boolean; executor: string;
  model_identity?: string | null; execution_identity?: string | null;
  reason_code?: string | null; checking?: boolean;
  qualification_state?: string; qualification_identity?: string | null; production_eligible?: boolean;
};
type State = {
  status: string; retry_available: boolean; start_available?: boolean; summary_recovery?: boolean;
  last_failure_category?: string | null; capability?: TranscriptionCapability;
};
const stateCopy: Record<string, string> = {
  PENDING: "Awaiting transcription", RUNNING: "Transcribing…", READY: "Transcription complete",
  RUNTIME_UNAVAILABLE: "Local transcription is unavailable", MODEL_MISSING: "Local model is missing",
  UNSUPPORTED: "Local executor is incompatible", FAILED: "Local transcription failed", INTERRUPTED: "Transcription was interrupted",
  QUALIFICATION_REQUIRED: "Acoustic qualification required",
};
const qualificationCopy: Record<string, string> = {
  NOT_TESTED: "Not tested", RUNNING: "Qualification running…", PASSED: "Qualification passed",
  FAILED: "Acoustic qualification failed", STALE: "Qualification stale",
};
const reasons: Record<string, string> = {
  CAPABILITY_CHECKING: "Checking local transcription capability…",
  RUNTIME_UNAVAILABLE: "A compatible local MLX runtime is required. Existing transcripts remain readable.",
  MODEL_MISSING: "Provide a local MLX Whisper model directory to enable offline transcription. No model is downloaded automatically.",
  EXECUTOR_INCOMPATIBLE: "The local runtime or model is incompatible with timed transcription.",
  MODEL_INVALID: "The selected local model directory could not be verified.",
  EXECUTOR_TIMEOUT: "Transcription exceeded its time limit. You can retry the selected executor.",
  EXECUTOR_FAILED: "The selected local executor could not transcribe this media. You can retry.",
  EXECUTOR_OUTPUT_LIMIT: "The local executor exceeded its output limit. No transcript was accepted.",
  TRANSCRIPT_INVALID: "The executor returned invalid text or timestamps. No transcript was accepted.",
  LOCAL_SOURCE_UNTRUSTED: "The imported snapshot failed verification. Existing Evidence is unavailable.",
  MODEL_CHANGED: "The model changed during execution. Check the selected model and retry.",
  EXECUTOR_IDENTITY_CHANGED: "The selected executor or model changed. Review the current selection before retrying.",
  TRANSCRIPTION_BUSY: "Another local transcription is running. Try again shortly.",
  MEDIA_TOOL_UNAVAILABLE: "Local transcription requires compatible ffmpeg and ffprobe tools.",
  LOCAL_INVALID_MEDIA: "This media file is malformed, has a mismatched format or exceeds two hours.",
  INTERRUPTED: "Transcription was interrupted. You can start a new attempt.",
  ACOUSTIC_NOT_QUALIFIED: "Installed models require acoustic qualification before new transcription. Existing transcripts remain readable.",
};
export const transcriptionCopy = (status: string) => stateCopy[status] ?? "Local transcription is unavailable";
export function LocalTranscription({ id, onCompleted, onStatusChange }: { id: string; onCompleted: () => void; onStatusChange?: (status: string) => void }) {
  const { t } = useUiLanguage();
  const [state, setState] = useState<State | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [modelPath, setModelPath] = useState("");
  const [revision, setRevision] = useState(0);
  const completed = useRef(false);
  const onComplete = useRef(onCompleted); onComplete.current = onCompleted;
  const onStatus = useRef(onStatusChange); onStatus.current = onStatusChange;
  useEffect(() => {
    let active = true; let timer: ReturnType<typeof setTimeout> | undefined;
    const read = async () => {
      try {
        const response = await api<{ transcription: State }>(`/videos/${encodeURIComponent(id)}/transcription`);
        if (!active) return;
        setState(response.transcription); setError(null);
        onStatus.current?.(response.transcription.status);
        if (response.transcription.status === "READY" && !completed.current) {
          completed.current = true; onComplete.current();
        }
        if (["RUNNING", "PENDING"].includes(response.transcription.status) && !response.transcription.start_available || response.transcription.capability?.checking || response.transcription.capability?.qualification_state === "RUNNING") {
          timer = setTimeout(read, 2000);
        }
      } catch (reason) {
        if (active) setError(reason instanceof ApiRequestError ? reasons[reason.code] ?? "Local transcription could not complete. Check diagnostics and retry." : "Local transcription could not complete. Check diagnostics and retry.");
      }
    };
    void read();
    return () => { active = false; if (timer) clearTimeout(timer); };
  }, [id, revision]);
  const action = async (kind: "start" | "refresh" | "model") => {
    if (busy) return; setBusy(true); setError(null);
    try {
      if (kind === "start") await post(`/videos/${encodeURIComponent(id)}/transcription`, { execution_identity: state?.summary_recovery ? "summary-recovery" : state?.capability?.execution_identity });
      if (kind === "refresh") await post("/local/transcription/refresh", {});
      if (kind === "model") { await put("/local/transcription/model", { model_path: modelPath.trim() || null }); setModelPath(""); }
      setRevision(value => value + 1);
    } catch (reason) {
      setError(reason instanceof ApiRequestError ? reasons[reason.code] ?? "Local transcription could not complete. Check diagnostics and retry." : "Local transcription could not complete. Check diagnostics and retry.");
    } finally { setBusy(false); }
  };
  const capability = state?.capability;
  const active = state?.status === "RUNNING" || capability?.checking;
  return <section className="local-transcription" aria-label={t("Offline transcription")}>
    <p role="status" aria-live="polite">{t(capability?.checking ? reasons.CAPABILITY_CHECKING : transcriptionCopy(state?.status ?? "PENDING"))}</p>
    {state?.status !== "READY" && <p className="hint">{t(state?.status === "QUALIFICATION_REQUIRED" || ["MODEL_MISSING", "RUNTIME_UNAVAILABLE", "UNSUPPORTED"].includes(state?.status ?? "") ? transcriptionGuidance(capability) : reasons[state?.last_failure_category ?? capability?.reason_code ?? ""] ?? "Transcription runs on this device using the selected local executor and model. Your media stays private.")}</p>}
    {state && ["MODEL_MISSING", "RUNTIME_UNAVAILABLE", "UNSUPPORTED", "QUALIFICATION_REQUIRED"].includes(state.status) && <a className="button button-secondary" href={`#Settings/transcription/${encodeURIComponent(id)}`}>{t("Set up local transcription")}</a>}
    {error && <p role="alert">{t(error)}</p>}
    {(state?.start_available || state?.retry_available) && <button className="button button-primary" disabled={busy || active} onClick={() => void action("start")}>{t(state.summary_recovery ? "Complete Summary" : state.retry_available ? "Retry transcription" : "Start transcription")}</button>}
    <details><summary>{t("Transcription diagnostics")}</summary>
      <dl><dt>{t("Runtime detected")}</dt><dd>{t(capability?.runtime_detected ? "Yes" : "No")}</dd>
        <dt>{t("Runtime available")}</dt><dd>{t(capability?.runtime_available ? "Yes" : "No")}</dd>
        <dt>{t("Executor")}</dt><dd>{capability?.executor ?? "MLX Whisper"}</dd>
        <dt>{t("Model availability")}</dt><dd>{t(capability?.model_present ? "Available" : "Local model is missing")}</dd>
        <dt>{t("Acoustic qualification")}</dt><dd>{t(qualificationCopy[capability?.qualification_state ?? "NOT_TESTED"] ?? qualificationCopy.NOT_TESTED)}</dd>
        <dt>{t("Capability")}</dt><dd>{t(capability?.state === "READY" ? "Ready" : capability?.checking ? reasons.CAPABILITY_CHECKING : transcriptionCopy(capability?.state ?? "RUNTIME_UNAVAILABLE"))}</dd>
        {capability?.model_identity && <><dt>{t("Model identity")}</dt><dd>{capability.model_identity}</dd></>}
        {state?.last_failure_category && <><dt>{t("Failure category")}</dt><dd>{state.last_failure_category}</dd></>}
      </dl>
      <button className="button button-secondary" disabled={busy || active} onClick={() => void action("refresh")}>{t("Check availability")}</button>
      <label>{t("Local MLX model directory")}<input type="text" value={modelPath} maxLength={4096} placeholder={t("Choose an already provisioned local model directory")} autoComplete="off" onChange={event => setModelPath(event.target.value)} /></label>
      <button className="button button-secondary" disabled={busy || active || !modelPath.trim()} onClick={() => void action("model")}>{t("Use local model")}</button>
      <p className="hint">{t("Model configuration stays on this machine and is excluded from backups. Existing trusted transcripts do not require the model.")}</p>
    </details>
  </section>;
}
