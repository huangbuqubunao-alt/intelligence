import { useEffect, useRef, useState } from "react";
import { api, ApiRequestError, post, put } from "../api/client";
import type { TranscriptionCapability } from "./LocalTranscription";
import { useUiLanguage } from "./uiLanguage";

export function transcriptionGuidance(capability?: TranscriptionCapability) {
  if (!capability || capability.checking) return "Checking local transcription capability…";
  if (capability.reason_code === "MEDIA_TOOL_UNAVAILABLE") return "The media tools needed for local transcription are unavailable. Repair the application runtime, then check again. Text files can still be imported.";
  if (!capability.runtime_available) return "The local speech runtime is unavailable. Repair the application runtime, then check again. Your imported files are preserved.";
  if (capability.reason_code === "MODEL_INVALID") return "This directory is not a compatible local speech model. Choose the installed MLX Whisper model folder, then save and check again.";
  if (!capability.model_present) return "No local speech model is selected or its files are missing. Select an already installed model directory in Settings. Importing a video saves the file; it does not create a transcript.";
  if (!capability.executor_compatible) return "The selected speech model is incompatible with the local runtime. Choose a compatible installed model and check again.";
  if (capability.qualification_state === "FAILED") return "This model failed speech quality verification. Changing its directory will not remove this restriction. You can import a TXT or MD transcript while a verified model is unavailable.";
  if (capability.qualification_state === "STALE") return "The speech model or runtime changed since verification. New transcription is paused until the current combination passes quality verification. Existing transcripts remain readable.";
  if (capability.qualification_state === "RUNNING") return "Speech quality verification is in progress. New transcription remains paused until it passes.";
  if (capability.state !== "READY" || capability.production_eligible !== true) return "This speech model has not passed quality verification for use. Saving a directory does not qualify a model. You can import a TXT or MD transcript instead.";
  return "Local transcription is ready. Open an imported audio or video and choose Start transcription. Your media stays on this device.";
}

export function TranscriptionSetup() {
  const { t } = useUiLanguage();
  const [capability, setCapability] = useState<TranscriptionCapability>();
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState(false);
  const [readFailed, setReadFailed] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (location.hash.startsWith("#Settings/transcription")) {
      panel.current?.scrollIntoView?.({ block: "start" });
      panel.current?.focus({ preventScroll: true });
    }
  }, []);
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const read = async () => {
      try {
        const result = await api<{ capability: TranscriptionCapability }>("/local/transcription/capability");
        if (disposed) return;
        if (!result.capability?.state) throw new Error("Capability unavailable");
        setCapability(result.capability); setError(null); setReadFailed(false);
        if (result.capability.checking || result.capability.qualification_state === "RUNNING") timer = setTimeout(read, 2000);
      } catch {
        if (!disposed) { setReadFailed(true); setActionError(false); setError("Transcription status could not be checked. Check the local connection and try again."); }
      }
    };
    void read();
    return () => { disposed = true; if (timer) clearTimeout(timer); };
  }, [revision]);
  const check = async (save: boolean) => {
    if (busy) return;
    setBusy(true); setError(null); setMessage(null); setActionError(false);
    try {
      const result = save
        ? await put<{ capability: TranscriptionCapability }>("/local/transcription/model", { model_path: path.trim() })
        : await post<{ capability: TranscriptionCapability }>("/local/transcription/refresh", {});
      setCapability(result.capability);
      if (save) { setPath(""); setMessage("Model selection saved."); }
      setRevision(value => value + 1);
    } catch (reason) {
      setActionError(true);
      setError(reason instanceof ApiRequestError && reason.code === "MODEL_INVALID"
        ? "Enter the absolute path of an already installed local speech model directory. No model is downloaded automatically."
        : reason instanceof ApiRequestError && reason.code === "TRANSCRIPTION_BUSY"
        ? "Another local transcription or model check is running. Wait for it to finish, then try again."
        : "Transcription status could not be checked. Check the local connection and try again.");
    } finally { setBusy(false); }
  };
  const checking = busy || capability?.checking || capability?.qualification_state === "RUNNING";
  const match = /^#Settings\/transcription\/([^/]+)$/.exec(location.hash);
  let returnId: string | null = null;
  if (match) { try {
    const value = decodeURIComponent(match[1]);
    if (value && value.length <= 256 && !/[\p{Cc}\p{Cs}]/u.test(value)) returnId = value;
  } catch { /* Malformed links have no return target. */ } }
  return <section ref={panel} id="transcription-setup" tabIndex={-1} className="panel" aria-labelledby="transcription-setup-title">
    <h2 id="transcription-setup-title">{t("Local audio and video transcription")}</h2>
    <p role="status" aria-live="polite">{t(error && !capability ? error : transcriptionGuidance(capability))}</p>
    <p className="hint">{t("Importing a video saves the file. Transcript, Summary and Evidence require usable source text. You can also import an existing TXT or MD transcript; no cloud service is used for local transcription.")}</p>
    <button className="button button-secondary" disabled={busy || (!!checking && !readFailed)} onClick={() => readFailed ? setRevision(value => value + 1) : void check(false)}>{t(readFailed ? "Retry status check" : checking ? "Checking local transcription capability…" : "Check availability")}</button>
    <form onSubmit={event => { event.preventDefault(); if (path.trim()) void check(true); }}>
      <label className="field">{t("Local speech model directory")}<input value={path} maxLength={4096} autoComplete="off" placeholder={t("Choose an already provisioned local model directory")} disabled={!!checking || readFailed} onChange={event => setPath(event.target.value)} /></label>
      <button className="button button-primary" disabled={!!checking || readFailed || !path.trim()}>{t("Save and check model")}</button>
    </form>
    {message && <p role="status">{t(message)}</p>}
    {error && (capability || actionError) && <p className="form-error" role={actionError ? "alert" : "status"}>{t(error)}</p>}
    <p className="hint">{t("Use an already installed MLX Whisper model folder containing config.json and model weights. The app does not install runtimes or download models. Model configuration stays on this machine and is excluded from backups.")}</p>
    <details><summary>{t("Transcription diagnostics")}</summary>
      <dl><dt>{t("Runtime available")}</dt><dd>{capability ? t(capability.runtime_available ? "Yes" : "No") : t("Checking local transcription capability…")}</dd>
        <dt>{t("Model availability")}</dt><dd>{capability ? t(capability.model_present ? "Available" : "Local model is missing") : t("Checking local transcription capability…")}</dd>
        <dt>{t("Acoustic qualification")}</dt><dd>{t(({ PASSED: "Qualification passed", FAILED: "Acoustic qualification failed", STALE: "Qualification stale", RUNNING: "Qualification running…" } as Record<string, string>)[capability?.qualification_state ?? ""] ?? "Not tested")}</dd>
      </dl>
    </details>
    {returnId && <a className="button button-secondary" href={`#Content/${encodeURIComponent(returnId)}`}>{t("Back to Content")}</a>}
  </section>;
}
