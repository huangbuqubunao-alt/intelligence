import { useState } from "react";
import { api, ApiRequestError } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

const displayFilename = (name: string) => name.split(/[\\/]/).pop()?.replace(/[\p{Cc}\p{Cf}\p{Cs}]/gu, "").slice(0, 240) || "file";
const formats = new Set(["txt", "md", "mp3", "m4a", "wav", "mp4", "mov", "m4v"]);
const errorCopy: Record<string, string> = {
  LOCAL_UNSUPPORTED_FORMAT: "This file type is not supported. Choose TXT, MD, MP3, M4A, WAV, MP4, MOV or M4V.",
  LOCAL_INVALID_TEXT: "This text file must contain valid UTF-8 text without binary data.",
  LOCAL_INVALID_MEDIA: "This media file is malformed, has a mismatched format or exceeds two hours.",
  LOCAL_FILE_TOO_LARGE: "Choose text up to 2 MiB or media up to 64 MiB.",
  LOCAL_MEDIA_TOOL_UNAVAILABLE: "Local media validation requires ffprobe. Text files can still be imported.",
  LOCAL_IMPORT_BUSY: "Another local import is processing. Try again shortly.",
  LOCAL_SOURCE_UNTRUSTED: "The imported snapshot failed verification. Existing Evidence is unavailable.",
};
export function localStatus(status: string) {
  return ({ RUNNING: "Transcribing…", PENDING: "Awaiting transcription", MODEL_MISSING: "Local model is missing", INTERRUPTED: "Transcription was interrupted", READY: "Ready", IMPORTED: "Imported", TRANSCRIPTION_UNAVAILABLE: "Local transcription is unavailable", TRANSCRIPTION_FAILED: "Local transcription failed", FAILED: "Import failed", SOURCE_UNAVAILABLE: "Source verification failed" } as Record<string, string>)[status] ?? status;
}

type Result = { content_id: string; filename: string; status: string; duplicate: boolean };
export function LocalImport({ onClose, onSaved, onYouTube }: { onClose: () => void; onSaved: () => void; onYouTube: () => void }) {
  const { t } = useUiLanguage();
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [errors, setErrors] = useState<{ filename: string; message: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [finished, setFinished] = useState(false);
  const validate = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!formats.has(ext)) return errorCopy.LOCAL_UNSUPPORTED_FORMAT;
    if (!file.size || file.size > (ext === "txt" || ext === "md" ? 2 : 64) * 1024 * 1024) return errorCopy.LOCAL_FILE_TOO_LARGE;
    return null;
  };
  const confirm = async () => {
    if (busy || finished) return;
    setBusy(true); setErrors([]);
    for (const file of files) {
      try {
        const response = await api<{ import: Result }>(`/local/imports?filename=${encodeURIComponent(file.name)}`, { method: "POST", body: file, headers: { "Content-Type": "application/octet-stream" } });
        setResults(values => [...values, response.import]);
      } catch (reason) {
        const message = reason instanceof ApiRequestError ? errorCopy[reason.code] : null;
        setErrors(values => [...values, { filename: displayFilename(file.name), message: message ?? "The selected file could not be imported. Try again after checking local storage." }]);
      }
    }
    setFinished(true); setBusy(false);
  };
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-labelledby="local-import-title">
    <div className="modal-head"><h2 id="local-import-title">{t("Add local files")}</h2><button className="button button-ghost" disabled={busy} onClick={finished ? onSaved : onClose}>{t(finished ? "Done" : "Cancel")}</button></div>
    {!finished && <div className="button-row" aria-label={t("Source provider")}><button className="button button-secondary" disabled={busy} onClick={onYouTube}>YouTube</button><button className="button button-primary" aria-pressed="true" disabled={busy}>{t("Local files")}</button></div>}
    <p>{t("Import a private snapshot into your Local library. Originals stay untouched; moving, deleting or editing them does not change imported Content.")}</p>
    <p className="hint">{t("TXT / MD: UTF-8, up to 2 MiB. Audio / video: up to 64 MiB and two hours. Everything stays on this device.")}</p>
    {!finished && <label className="field">{t("Choose local files")}<input type="file" aria-label={t("Choose local files")} multiple accept=".txt,.md,.mp3,.m4a,.wav,.mp4,.mov,.m4v" disabled={busy} onChange={event => {
      const selected = Array.from(event.target.files ?? []);
      setResults([]); setErrors([]);
      if (selected.length > 20) { setFiles([]); setErrors([{ filename: "", message: "Choose up to 20 files at a time." }]); return; }
      const invalid = selected.flatMap(file => { const message = validate(file); return message ? [{ filename: displayFilename(file.name), message }] : []; });
      setErrors(invalid);
      setFiles(selected.filter(file => !validate(file)));
    }} /></label>}
    {!finished && files.length > 0 && <ul className="local-file-list">{files.map((file, index) => <li key={index}>{displayFilename(file.name)}</li>)}</ul>}
    {errors.map((error, index) => <p role="alert" className="form-error" key={index}>{error.filename && <strong>{error.filename}: </strong>}{t(error.message)}</p>)}
    {busy && <p role="status">{t("Importing selected files…")}</p>}
    {results.length > 0 && <ul className="local-file-list">{results.map((result, index) => <li key={index}><strong>{result.filename}</strong><p>{t(localStatus(result.status))}{result.duplicate ? ` · ${t("Already imported")}` : ""}</p><a href={`#Content/${result.content_id}`} onClick={onSaved}>{t("Open Content")}</a></li>)}</ul>}
    {results.some(result => result.status === "TRANSCRIPTION_UNAVAILABLE") && <p className="hint">{t("Media snapshots are saved. A provisioned offline transcription adapter is required for transcript, Summary and Evidence; nothing is sent to a cloud service.")}</p>}
    {!finished && <button className="button button-primary" disabled={busy || !files.length} onClick={() => void confirm()}>{t("Confirm import")}</button>}
    {finished && <button className="button button-primary" onClick={onSaved}>{t("Done")}</button>}
  </section></div>;
}
