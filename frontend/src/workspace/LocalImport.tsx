import { useEffect, useRef, useState } from "react";
import { uploadLocal, ApiRequestError, api } from "../api/client";
import { scheduleSafeHashUpdate } from "./motion";
import { NativeLocalImport } from "./NativeLocalImport";
import { useUiLanguage } from "./uiLanguage";

const displayFilename = (name: string) => name.split(/[\\/]/).pop()?.replace(/[\p{Cc}\p{Cf}\p{Cs}]/gu, "").slice(0, 240) || "file";
const formats = new Set(["txt", "md", "mp3", "m4a", "wav", "mp4", "mov", "m4v"]);
export const localImportErrors: Record<string, string> = {
  LOCAL_UNSUPPORTED_FORMAT: "This file type is not supported. Choose TXT, MD, MP3, M4A, WAV, MP4, MOV or M4V.",
  LOCAL_INVALID_TEXT: "This text file must contain valid UTF-8 text without binary data.",
  LOCAL_INVALID_MEDIA: "This media file is malformed or has a mismatched format.",
  LOCAL_FILE_TOO_LARGE: "Choose text up to 2 MiB or media up to 2 GiB.",
  LOCAL_BACKUP_CAPACITY_EXCEEDED: "The local library has reached its safe backup capacity. This file was not saved.",
  LOCAL_MEDIA_TOO_LONG: "This media exceeds the four-hour duration limit. Choose a shorter recording.",
  LOCAL_EMPTY_FILE: "This file is empty. Choose a file containing text or media.",
  LOCAL_DISK_SPACE_INSUFFICIENT: "There is not enough available disk space. Free space on this device and retry.",
  LOCAL_FILE_UNREADABLE: "Local storage could not be written safely. Check its availability and permissions.",
  LOCAL_IMPORT_INTERRUPTED: "The local connection was interrupted. Retry the file; a saved copy will be recognized automatically.",
  LOCAL_IMPORT_TIMEOUT: "Import timed out. Check the local connection and retry the file.",
  LOCAL_IMPORT_CANCELLED: "Import cancelled. If saving already completed, retrying will recognize the saved Content.",
  LOCAL_MEDIA_TOOL_UNAVAILABLE: "Local media validation requires ffprobe. Text files can still be imported.",
  LOCAL_IMPORT_BUSY: "Another local import is processing. Try again shortly.",
  LOCAL_SOURCE_UNTRUSTED: "The imported snapshot failed verification. Existing Evidence is unavailable.",
  LOCAL_NATIVE_PICKER_FAILED: "The macOS file selector could not complete. Reopen it and choose files again.",
  LOCAL_NATIVE_ACCESS_REJECTED: "Native file access was rejected. Reopen Intelligence using its current launcher.",
  LOCAL_SELECTION_EXPIRED: "This file selection expired or was already used. Choose the file again.",
  LOCAL_SELECTED_FILE_CHANGED: "The selected file changed before import. Choose it again to authorize its current version.",
};
/**
 * Local processing states carry their own wording, so each one resolves to a
 * sentence the user can act on.  A stored snapshot that no longer verifies has
 * its own copy: the interface states that its Evidence is unavailable instead
 * of naming a backend code the user cannot act on.
 */
const statusCopy: Record<string, string> = {
  RUNNING: "Transcribing…",
  PENDING: "Awaiting transcription",
  MODEL_MISSING: "Local model is missing",
  INTERRUPTED: "Transcription was interrupted",
  READY: "Ready",
  IMPORTED: "Imported",
  UNAVAILABLE: "Unavailable",
  NOT_PROCESSED: "Not processed",
  // This saved snapshot status is historical; Content owns the live job/capability.
  TRANSCRIPTION_UNAVAILABLE: "File saved",
  TRANSCRIPTION_FAILED: "Local transcription failed",
  FAILED: "Import failed",
  SOURCE_UNAVAILABLE: "Source verification failed",
  SOURCE_UNTRUSTED: "The imported snapshot failed verification. Existing Evidence is unavailable.",
  LOCAL_SOURCE_UNTRUSTED: "The imported snapshot failed verification. Existing Evidence is unavailable.",
};
/**
 * A code with no honest equivalent is reported as an unknown state rather than
 * displayed as the raw enum, so backend vocabulary never reaches the interface
 * and never has to be de-CamelCased into a sentence nobody chose.
 */
export function localStatus(status: string) {
  return statusCopy[status] ?? "This Content is in a state that cannot be explained yet.";
}

type Result = { content_id: string; filename: string; status: string; duplicate: boolean };
export function LocalImport({ onClose, onSaved, onImported, onYouTube, onBilibili }: { onClose: () => void; onSaved: () => void; onImported?: (contentId: string) => void; onYouTube: () => void; onBilibili?: () => void }) {
  const { t } = useUiLanguage();
  const nativeMac = navigator.platform.includes("Mac");
  const [nativeAvailable, setNativeAvailable] = useState<boolean | null>(null);
  useEffect(() => {
    if (!nativeMac) return;
    let disposed = false;
    void api<{ capability: { available: boolean } }>("/local/native/capability")
      .then(response => { if (!disposed) setNativeAvailable(response.capability.available); })
      .catch(() => { if (!disposed) setNativeAvailable(false); });
    return () => { disposed = true; };
  }, [nativeMac]);
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [selectionErrors, setSelectionErrors] = useState<{ filename: string; message: string }[]>([]);
  const [errors, setErrors] = useState<{ filename: string; message: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(false);
  const submitting = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const [progress, setProgress] = useState<{ filename: string; loaded: number; total: number } | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [failedFiles, setFailedFiles] = useState<File[]>([]);
  const [useBrowserUpload, setUseBrowserUpload] = useState(false);
  const done = () => results.length && onImported ? onImported(results[0].content_id) : results.length ? onSaved() : onClose();
  useEffect(() => {
    if (nativeMac && !useBrowserUpload) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) {
        event.preventDefault();
        if (finished) done();
        else onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [nativeMac, useBrowserUpload, busy, finished, results.length]);
  const validate = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!formats.has(ext)) return localImportErrors.LOCAL_UNSUPPORTED_FORMAT;
    if (!file.size) return localImportErrors.LOCAL_EMPTY_FILE;
    if (file.size > (ext === "txt" || ext === "md" ? 2 * 1024 * 1024 : 2 * 1024 * 1024 * 1024)) return localImportErrors.LOCAL_FILE_TOO_LARGE;
    return null;
  };
  const confirm = async (selected = files) => {
    if (submitting.current || !selected.length) return;
    submitting.current = true;
    setBusy(true); setFinished(false); setErrors([]);
    controller.current = new AbortController();
    const signal = controller.current.signal;
    const accepted: Result[] = [];
    const failed: File[] = [];
    for (const file of selected) {
      setProgress(null); setVerifying(false);
      try {
        const response = await uploadLocal<{ import: Result }>(`/local/imports?filename=${encodeURIComponent(file.name)}`, file, signal,
          (loaded, total) => setProgress({ filename: displayFilename(file.name), loaded, total }), () => setVerifying(true));
        accepted.push(response.import);
        setResults(values => [...values, response.import]);
      } catch (reason) {
        failed.push(file);
        const message = signal.aborted ? localImportErrors.LOCAL_IMPORT_CANCELLED : reason instanceof ApiRequestError ? localImportErrors[reason.code] : null;
        setErrors(values => [...values, { filename: displayFilename(file.name), message: message ?? "The selected file could not be imported. Try again after checking local storage." }]);
      }
    }
    setFailedFiles(failed); setFinished(true); setBusy(false);
    submitting.current = false; controller.current = null;
    // Only committed success navigates. Mixed batches keep per-file outcomes visible.
    if (!failed.length && !selectionErrors.length && accepted.length && onImported) onImported((results[0] ?? accepted[0]).content_id);
  };
  if (nativeMac && !useBrowserUpload) return <NativeLocalImport available={nativeAvailable} onClose={onClose} onSaved={onSaved} onImported={onImported} onYouTube={onYouTube} onBilibili={onBilibili} onUseBrowserUpload={() => setUseBrowserUpload(true)} errors={localImportErrors} />;
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-labelledby="local-import-title">
    <div className="modal-head"><h2 id="local-import-title">{t("Add local files")}</h2><button className="button button-ghost" disabled={busy} onClick={finished ? done : onClose}>{t(finished ? "Done" : "Cancel")}</button></div>
    {!finished && <div className="button-row" aria-label={t("Source provider")}><button className="button button-secondary" disabled={busy} onClick={onYouTube}>YouTube / Bilibili</button><button className="button button-primary" aria-pressed="true" disabled={busy}>{t("Local files")}</button>{onBilibili && <button className="button button-secondary" disabled={busy} onClick={onBilibili}>{t("Bilibili")}</button>}</div>}
    <p>{t("Import a private snapshot into your Local library. Originals stay untouched; moving, deleting or editing them does not change imported Content.")}</p>
    <p className="hint">{t("TXT / MD: UTF-8, up to 2 MiB. Audio / video: up to 2 GiB. Media duration: up to four hours. Everything stays on this device.")}</p>
    <p className="hint">{t("Importing a video saves the file. Transcript, Summary and Evidence require usable source text. You can also import an existing TXT or MD transcript; no cloud service is used for local transcription.")}</p>
    <button className="button button-ghost" disabled={busy} onClick={() => { onClose(); scheduleSafeHashUpdate("Settings/transcription"); }}>{t("Set up local transcription")}</button>
    {!finished && <label className="field">{t("Choose local files")}<input type="file" aria-label={t("Choose local files")} multiple accept=".txt,.md,.mp3,.m4a,.wav,.mp4,.mov,.m4v" disabled={busy} onChange={event => {
      const selected = Array.from(event.target.files ?? []);
      setResults([]); setErrors([]);
      if (selected.length > 20) { setFiles([]); setErrors([{ filename: "", message: "Choose up to 20 files at a time." }]); setSelectionErrors([]); return; }
      const invalid = selected.flatMap(file => { const message = validate(file); return message ? [{ filename: displayFilename(file.name), message }] : []; });
      setSelectionErrors(invalid);
      setFiles(selected.filter(file => !validate(file)));
    }} /></label>}
    {!finished && files.length > 0 && <ul className="local-file-list">{files.map((file, index) => <li key={index}>{displayFilename(file.name)}</li>)}</ul>}
    {[...selectionErrors, ...errors].map((error, index) => <p role="alert" className="form-error" key={index}>{error.filename && <strong>{error.filename}: </strong>}{t(error.message)}</p>)}
    {busy && <div><p role="status" aria-live="polite">{t(verifying ? "Verifying imported file…" : "Importing selected files…")}</p>
      {progress && !verifying && <><p>{progress.filename}: {Math.floor(progress.loaded / progress.total * 100)}%</p><progress aria-label={t("Upload progress")} value={progress.loaded} max={progress.total} /></>}
      <button className="button button-secondary" onClick={() => controller.current?.abort()}>{t("Cancel import")}</button>
    </div>}
    {results.length > 0 && <ul className="local-file-list">{results.map((result, index) => <li key={index}><strong>{result.filename}</strong><p>{t("Import successful. File saved.")}</p><p>{t(localStatus(result.status))}{result.duplicate ? ` · ${t("Already imported")}` : ""}</p>{!busy && <a href={`#Content/${result.content_id}`} onClick={event => { if (onImported) { event.preventDefault(); onImported(result.content_id); } else onSaved(); }}>{t("Open Content")}</a>}</li>)}</ul>}
    {results.some(result => result.status === "TRANSCRIPTION_UNAVAILABLE") && <p className="hint">{t("File saved. Open Content to check the current transcription status.")}</p>}
    {!finished && <button className="button button-primary" disabled={busy || !files.length} onClick={() => { if (!finished) void confirm(); }}>{t("Confirm import")}</button>}
    {finished && failedFiles.length > 0 && <button className="button button-secondary" onClick={() => void confirm(failedFiles)}>{t("Retry failed files")}</button>}
    {finished && <button className="button button-primary" onClick={done}>{t("Done")}</button>}
  </section></div>;
}
