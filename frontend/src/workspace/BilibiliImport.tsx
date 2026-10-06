import { CreatorFollowForm, CreatorFollowingCapabilityState, useCreatorFollowingCapability } from "./CreatorFollowing";
import { useState } from "react";
import { ApiRequestError, post } from "../api/client";
import { useUiLanguage } from "./uiLanguage";

const states: Record<string, string> = {
  READY: "Ready",
  IMPORTED: "Imported",
  CAPTION_UNAVAILABLE: "Public captions are unavailable",
  CAPTION_INVALID: "Public captions failed validation",
  NETWORK_UNAVAILABLE: "Bilibili is unreachable. Check your connection and try again.",
  RATE_LIMITED: "Bilibili requests are limited. Try again later.",
  ACCESS_DENIED: "This video or caption is not publicly accessible. Login and paid content are unsupported.",
  NOT_FOUND: "The public Bilibili video was not found.",
  INVALID_INPUT: "Enter a valid Bilibili BV video URL or BV id.",
  UNSUPPORTED_URL: "Use an HTTPS Bilibili BV video URL. Short links and other video parts are unsupported.",
  METADATA_FAILED: "Bilibili metadata could not be verified. Try again later.",
  DURATION_UNSUPPORTED: "This video exceeds the supported two-hour limit.",
  SOURCE_UNTRUSTED: "The stored Bilibili source failed verification. Its Evidence is unavailable.",
  SOURCE_UNAVAILABLE: "The stored Bilibili source failed verification. Its Evidence is unavailable.",
  STORAGE_UNAVAILABLE: "Content storage is unavailable. Check local storage and try again.",
};
export function bilibiliStatus(code: string) {
  return states[code.replace(/^BILIBILI_/, "")] ?? "The public Bilibili video could not be imported. Try again later.";
}
const noCaptionCopy = "This Content has metadata only. Summary and Evidence require trusted captions. No video is downloaded or transcribed.";
type Result = { content_id: string; processing_status: string; reused: boolean };

export function BilibiliImport({ onClose, onSaved, onProvider }: {
  onClose: () => void; onSaved: () => void; onProvider: (provider: "YOUTUBE" | "LOCAL") => void;
}) {
  const { t } = useUiLanguage();
  const capability: CreatorFollowingCapabilityState = useCreatorFollowingCapability();
  // "Follow a creator" is only offered when the service says it works.
  const creatorOff = capability.known && capability.capability !== null && !capability.capability.available;
  const [mode, setMode] = useState<"video" | "creator">("video");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const submit = async () => {
    if (busy || !input.trim() || result) return;
    setBusy(true); setError(null);
    try {
      const response = await post<{ import: Result }>("/bilibili/imports", { input: input.trim() });
      setResult(response.import);
    } catch (reason) {
      setError(bilibiliStatus(reason instanceof ApiRequestError ? reason.code : "NETWORK_UNAVAILABLE"));
    } finally { setBusy(false); }
  };
  return <div className="overlay"><section className="modal local-import" role="dialog" aria-modal="true" aria-labelledby="bilibili-import-title">
    <div className="modal-head"><h2 id="bilibili-import-title">{t(mode === "creator" ? "Follow Bilibili creator" : "Add Bilibili video")}</h2><button className="button button-ghost" disabled={busy} onClick={result ? onSaved : onClose}>{t(result ? "Done" : "Cancel")}</button></div>
    {!result && <div className="button-row" aria-label={t("Source provider")}>
      <button className="button button-secondary" disabled={busy} onClick={() => onProvider("YOUTUBE")}>YouTube</button>
      <button className="button button-secondary" disabled={busy} onClick={() => onProvider("LOCAL")}>{t("Local files")}</button>
      <button className="button button-primary" aria-pressed="true" disabled={busy}>{t("Bilibili")}</button>
    </div>}
    {/* The creator entry point is only offered once the service has confirmed
        it works, so an entry point that may turn out to be unavailable is never
        shown and then taken away. */}
    {!result && capability.known && !creatorOff && <div className="button-row" aria-label={t("Bilibili source type")}>
      <button className="button button-secondary" disabled={busy} aria-pressed={mode === "video"} onClick={() => setMode("video")}>{t("Add one video")}</button>
      <button className="button button-secondary" disabled={busy} aria-pressed={mode === "creator"} onClick={() => setMode("creator")}>{t("Follow a creator")}</button>
    </div>}
    {!capability.known && !result && <p role="status">{t("Checking whether this is available…")}</p>}
    {creatorOff && <p className="hint">{t("Continuous Bilibili creator tracking is currently unavailable. You can still add public Bilibili videos.")}</p>}
    {mode === "creator" ? <CreatorFollowForm capability={capability} onSaved={onSaved} /> : <>
    <p>{t("Import one public Bilibili video. This does not follow its creator. No account or cookies are needed.")}</p>
    {!result && <form onSubmit={event => { event.preventDefault(); void submit(); }}>
      <label className="field">{t("Bilibili video URL or BV id")}<input autoFocus aria-label={t("Bilibili video URL or BV id")} value={input} maxLength={2048} disabled={busy} onChange={event => setInput(event.target.value)} placeholder="https://www.bilibili.com/video/BV…/" /></label>
      <p className="hint">{t("Only public metadata and available timed captions are retrieved. Captions keep their original text and language.")}</p>
      <button className="button button-primary" disabled={busy || !input.trim()}>{t(busy ? "Importing public video…" : "Import public video")}</button>
    </form>}
    {error && <p role="alert" className="form-error">{t(error)}</p>}
    {busy && <p role="status">{t("Importing public video…")}</p>}
    {result && <div role="status"><p>{t(bilibiliStatus(result.processing_status))}{result.reused ? ` · ${t("Already imported")}` : ""}</p>
      {result.processing_status !== "READY" && <p className="hint">{t(noCaptionCopy)}</p>}
      <a href={`#Content/${result.content_id}`} onClick={onSaved}>{t("Open Content")}</a>
    </div>}
    </>}
  </section></div>;
}

export function BilibiliCaptionStatus({ id, status, onCompleted }: { id: string; status: string; onCompleted: () => void }) {
  const { t } = useUiLanguage();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const retry = async () => {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      await post(`/videos/${id}/captions/retry`, {});
      onCompleted();
    } catch (reason) { setError(bilibiliStatus(reason instanceof ApiRequestError ? reason.code : "NETWORK_UNAVAILABLE")); }
    finally { setBusy(false); }
  };
  return <div className="semantic-state state-neutral" aria-live="polite">
    <p>{t(status === "READY" ? "These are stored original Bilibili timed captions. Reading them does not contact Bilibili." : noCaptionCopy)}</p>
    {status !== "READY" && <><p>{t(bilibiliStatus(status))}</p><button className="button button-secondary" disabled={busy || status === "SOURCE_UNAVAILABLE"} onClick={() => void retry()}>{t(busy ? "Checking public captions…" : "Retry public captions")}</button></>}
    {error && <p role="alert">{t(error)}</p>}
  </div>;
}
