import { useEffect, useRef, useState } from "react";
import { ApiRequestError, api, post } from "../api/client";
import { scheduleSafeHashUpdate } from "./motion";
import { useUiLanguage } from "./uiLanguage";

export type NativeFileState = {
  filename: string; byte_count: number; phase: string; loaded: number;
  snapshot_method: string; error_code: string | null; processing_error_code: string | null;
  import: { content_id: string; filename: string; status: string; duplicate: boolean } | null;
};
export type NativeJob = { job_id: string; state: string; files: NativeFileState[]; error_code: string | null };
const running = (job: NativeJob) => ["SELECTING", "IMPORTING"].includes(job.state);
const terminalNotice = (job: NativeJob) => ["FAILED", "COMPLETE"].includes(job.state);
const changed = (job: NativeJob) => window.dispatchEvent(new CustomEvent("native-imports-changed", { detail: job }));
const phaseCopy: Record<string, string> = {
  SELECTED: "Ready to add", SNAPSHOTTING: "Creating local snapshot…", COPYING: "Copying local file…",
  VERIFYING: "Verifying imported file…", SAVED: "Import successful. File saved.", FAILED: "Import failed",
};

function FileState({ file, errors }: { file: NativeFileState; errors?: Record<string, string> }) {
  const { t } = useUiLanguage();
  return <li><strong>{file.filename}</strong><p role="status">{t(phaseCopy[file.phase] ?? "Importing selected files…")}</p>
    {file.phase === "COPYING" && file.byte_count > 0 && <><p>{Math.floor(file.loaded / file.byte_count * 100)}%</p><progress aria-label={t("Copy progress")} value={file.loaded} max={file.byte_count} /></>}
    {file.error_code && <p role="alert" className="form-error">{t(errors?.[file.error_code] ?? "The selected file could not be imported. Try again after checking local storage.")}</p>}
    {file.import && <p>{t(file.import.status === "READY" ? "Ready" : "File saved. Local transcription status appears in Content.")}{file.import.duplicate ? ` · ${t("Already imported")}` : ""}</p>}
    {file.processing_error_code && <p>{t("File saved. Further processing could not complete; check its status in Content.")}</p>}
  </li>;
}

export function NativeLocalImport({ available, onClose, onSaved, onImported, onYouTube, onBilibili, errors }: {
  available: boolean | null; onClose: () => void; onSaved: () => void;
  onImported?: (id: string) => void; onYouTube: () => void; onBilibili?: () => void;
  errors: Record<string, string>;
}) {
  const { t } = useUiLanguage();
  const [job, setJob] = useState<NativeJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [pollRevision, setPollRevision] = useState(0);
  const acted = useRef(false);
  const received = (next: NativeJob) => { setJob(next); changed(next); };
  const explain = (reason: unknown) => setError(reason instanceof ApiRequestError ? errors[reason.code] ?? "The selected file could not be imported. Try again after checking local storage." : "The local service could not be reached. Reopen Intelligence and retry.");
  useEffect(() => {
    if (!job || !running(job)) return;
    let disposed = false;
    const timer = setTimeout(async () => {
      try {
        const response = await post<{ job: NativeJob }>(`/local/native/picks/${job.job_id}`, {});
        if (!disposed) received(response.job);
      } catch (reason) { if (!disposed) { explain(reason); setPollRevision(value => value + 1); } }
    }, 500);
    return () => { disposed = true; clearTimeout(timer); };
  }, [job, pollRevision]);
  useEffect(() => {
    if (!job || acted.current || job.error_code || job.files.some(file => file.error_code) || !job.files.length || !job.files.every(file => file.import)) return;
    acted.current = true;
    if (onImported) onImported(job.files[0].import!.content_id);
    else onSaved();
  }, [job, onImported, onSaved]);
  const request = async (action: "choose" | "confirm" | "cancel") => {
    if (pending) return;
    setPending(true); setError(null);
    try {
      const path = action === "choose" ? "/local/native/picks" : `/local/native/picks/${job!.job_id}/${action}`;
      const response = await post<{ job: NativeJob }>(path, {});
      received(response.job);
    } catch (reason) { explain(reason); }
    finally { setPending(false); }
  };
  const busy = !!job && running(job);
  const close = async () => {
    if (job?.state === "SELECTED" || job?.state === "SELECTING") await request("cancel");
    onClose();
  };
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-labelledby="native-local-title">
    <div className="modal-head"><h2 id="native-local-title">{t("Add local files")}</h2><button className="button button-ghost" disabled={pending} onClick={() => void close()}>{t(busy && job?.state === "IMPORTING" ? "Continue in background" : "Cancel")}</button></div>
    <div className="button-row" aria-label={t("Source provider")}><button className="button button-secondary" disabled={busy || pending} onClick={onYouTube}>YouTube / Bilibili</button><button className="button button-primary" aria-pressed="true" disabled={busy}>{t("Local files")}</button>{onBilibili && <button className="button button-secondary" disabled={busy || pending} onClick={onBilibili}>{t("Bilibili")}</button>}</div>
    <p>{t("Choose files in the macOS selector. Intelligence creates independent local snapshots; file contents are not uploaded through the browser.")}</p>
    <p className="hint">{t("TXT / MD: UTF-8, up to 2 MiB. Audio / video: up to 2 GiB. Media duration: up to four hours. Everything stays on this device.")}</p>
    <p className="hint">{t("Importing a video saves the file. Transcript, Summary and Evidence require usable source text. You can also import an existing TXT or MD transcript; no cloud service is used for local transcription.")}</p>
    <button className="button button-ghost" disabled={busy || pending} onClick={() => void close().then(() => { scheduleSafeHashUpdate("Settings/transcription"); })}>{t("Set up local transcription")}</button>
    {available === null && <p role="status">{t("Checking native file selection…")}</p>}
    {available === false && <p role="alert" className="form-error">{t("Native file selection is unavailable. Reopen Intelligence using its current launcher.")}</p>}
    {error && <p role="alert" className="form-error">{t(error)}</p>}
    {job?.error_code && <p role="alert" className="form-error">{t(errors[job.error_code] ?? "The selected file could not be imported. Try again after checking local storage.")}</p>}
    {job?.state === "SELECTING" && <p role="status">{t("Choose files in the macOS selector…")}</p>}
    {job?.state === "IMPORTING" && <p role="status">{t("Importing selected files…")}</p>}
    {job?.state === "CANCELLED" && <p role="status">{t("Selection cancelled. No new Content was added.")}</p>}
    {!!job?.files.length && <ul className="local-file-list">{job.files.map((file, index) => <FileState key={index} file={file} errors={errors} />)}</ul>}
    {!busy && <button className="button button-secondary" aria-label={t("Choose local files")} disabled={available !== true || pending || job?.state === "SELECTED"} onClick={() => { acted.current = false; void request("choose"); }}>{t("Choose local files")}</button>}
    {job?.state === "SELECTED" && <button className="button button-primary" disabled={pending} onClick={() => void request("confirm")}>{t("Confirm import")}</button>}
    {busy && <button className="button button-secondary" disabled={pending} onClick={() => void request("cancel")}>{t("Cancel import")}</button>}
    {job?.files.filter(file => file.import).map((file, index) => <button key={index} className="button button-primary" onClick={() => onImported ? onImported(file.import!.content_id) : onSaved()}>{t("Open Content")}: {file.filename}</button>)}
  </section></div>;
}

/** Pending work is visible outside the modal while the rest of the app works. */
export function NativeImportActivity({ onOpen, errors, routeKey = "", modalOpen = false }: { onOpen: (id: string) => void; errors?: Record<string, string>; routeKey?: string; modalOpen?: boolean }) {
  const { t } = useUiLanguage();
  const [jobs, setJobs] = useState<NativeJob[]>([]);
  const acknowledged = useRef(new Set<string>());
  const known = useRef(new Set<string>());
  const expires = useRef(new Map<string, number>());
  const modal = useRef(modalOpen); modal.current = modalOpen;
  const route = useRef(routeKey);
  const dismiss = (id: string) => {
    acknowledged.current.add(id);
    expires.current.delete(id);
    setJobs(current => current.filter(job => job.job_id !== id || running(job)));
  };
  useEffect(() => {
    if (route.current === routeKey) return;
    route.current = routeKey;
    setJobs(current => {
      current.filter(job => !running(job)).forEach(job => acknowledged.current.add(job.job_id));
      return current.filter(running);
    });
  }, [routeKey]);
  useEffect(() => {
    const notices = jobs.filter(job => !running(job));
    if (!notices.length) return;
    const deadline = Math.min(...notices.map(job => expires.current.get(job.job_id) ?? Date.now()));
    const timer = setTimeout(() => notices.forEach(job => {
      if ((expires.current.get(job.job_id) ?? 0) <= Date.now()) dismiss(job.job_id);
    }), Math.max(0, deadline - Date.now()));
    return () => clearTimeout(timer);
  }, [jobs]);
  useEffect(() => {
    if (!navigator.platform.includes("Mac")) return;
    let disposed = false, active = false, loaded = false, reading = false, queued = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const receive = (incoming: NativeJob[], initial = false) => {
      const visible = incoming.filter(job => {
        if (terminalNotice(job) && initial && !known.current.has(job.job_id)) acknowledged.current.add(job.job_id);
        known.current.add(job.job_id);
        if (terminalNotice(job) && !expires.current.has(job.job_id)) expires.current.set(job.job_id, Date.now() + 15000);
        return job.state === "IMPORTING" || ((job.state === "FAILED" || job.state === "COMPLETE") && !acknowledged.current.has(job.job_id));
      });
      setJobs(visible);
    };
    const update = async () => {
      if (!active || disposed || reading) return;
      reading = true;
      try {
        const result = await post<{ jobs: NativeJob[] }>("/local/native/jobs", {});
        if (!disposed) {
          receive(result.jobs, !loaded); loaded = true;
          if (timer) clearTimeout(timer);
          if (result.jobs.some(running)) timer = setTimeout(update, 1000);
        }
      } catch {
        // Keep tracking a live import across a temporary API restart.
        if (!disposed) timer = setTimeout(update, 2000);
      } finally {
        reading = false;
        if (queued && !disposed) { queued = false; void update(); }
      }
    };
    const changed = (event: Event) => {
      const job = (event as CustomEvent<NativeJob>).detail;
      if (job?.job_id) {
        known.current.add(job.job_id);
        // Only this dialog's actual terminal event acknowledges its result.
        // SELECTED is still waiting for confirmation, and other jobs may finish
        // while an unrelated Add dialog is open.
        if (terminalNotice(job) && modal.current) acknowledged.current.add(job.job_id);
      }
      if (reading) queued = true;
      else void update();
    };
    void api<{ capability: { available: boolean } }>("/local/native/capability").then(result => { active = result.capability.available; void update(); }).catch(() => {});
    window.addEventListener("native-imports-changed", changed);
    return () => { disposed = true; if (timer) clearTimeout(timer); window.removeEventListener("native-imports-changed", changed); };
  }, []);
  const visible = jobs.filter(job => job.state === "IMPORTING" || job.state === "FAILED" || job.state === "COMPLETE");
  return visible.length ? <section className="panel" aria-label={t("Local imports")}><h2>{t("Local imports")}</h2>
    {visible.map(job => <div key={job.job_id}>{!running(job) && <button className="button button-ghost" onClick={() => dismiss(job.job_id)}>{t("Dismiss import notice")}</button>}{job.error_code && <p role="alert">{t(errors?.[job.error_code] ?? "Import failed. Reopen local import to choose the file again.")}</p>}<ul className="local-file-list">{job.files.map((file, index) => <FileState key={index} file={file} errors={errors} />)}</ul>
      {job.files.filter(file => file.import).map((file, index) => <button key={index} className="button button-secondary" onClick={() => onOpen(file.import!.content_id)}>{t("Open Content")}: {file.filename}</button>)}
    </div>)}
  </section> : null;
}
